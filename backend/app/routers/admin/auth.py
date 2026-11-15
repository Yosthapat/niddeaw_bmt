from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.db_utils import rows
from app.deps import AnyAdminDep, SupabaseDep
from app.models.admin import AdminLoginRequest, AdminLoginResponse, AdminMe
from app.models.diagnostics import ClientIdentity
from app.security import create_access_token, verify_password
from app.services import login_throttle

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=AdminLoginResponse)
def login(
    payload: AdminLoginRequest, request: Request, supabase: SupabaseDep
) -> AdminLoginResponse:
    # Throttled per caller, not per username. Keying on the username would
    # mean anyone who knows the admin's name can lock them out of their own
    # panel on a club night by failing five logins on purpose.
    key = login_throttle.client_key(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )
    wait = login_throttle.retry_after_seconds(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts",
            headers={"Retry-After": str(wait)},
        )

    result = (
        supabase.table("admins")
        .select("id, username, password_hash, role, club_access, tournament_access")
        .eq("username", payload.username)
        .limit(1)
        .execute()
    )
    admin_rows = rows(result)
    if not admin_rows or not verify_password(payload.password, admin_rows[0]["password_hash"]):
        login_throttle.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )

    login_throttle.clear(key)
    admin_row = admin_rows[0]
    token = create_access_token(
        admin_id=admin_row["id"],
        role=admin_row["role"],
        club_access=_flag(admin_row.get("club_access"), True),
        tournament_access=_flag(admin_row.get("tournament_access"), False),
    )
    settings = get_settings()
    return AdminLoginResponse(access_token=token, expires_in_minutes=settings.jwt_expire_minutes)


def _flag(value: object, default: bool) -> bool:
    """A right as stored, or the default before 0046 added the column."""
    return default if value is None else bool(value)


@router.get("/me", response_model=AdminMe)
def me(supabase: SupabaseDep, admin: AnyAdminDep) -> AdminMe:
    """The signed-in admin and their rights, read fresh from the table, so
    a right taken away shows on the next screen rather than at the next
    login. (The routes themselves still go by the token until it expires.)"""
    found = rows(
        supabase.table("admins")
        .select("id, username, club_access, tournament_access")
        .eq("id", str(admin.admin_id))
        .limit(1)
        .execute()
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    row = found[0]
    return AdminMe(
        id=row["id"],
        username=row["username"],
        club_access=_flag(row.get("club_access"), True) and admin.club_access,
        tournament_access=_flag(row.get("tournament_access"), False) and admin.tournament_access,
    )


@router.get("/whoami", response_model=ClientIdentity)
def whoami(request: Request, admin: AnyAdminDep) -> ClientIdentity:
    """What the login throttle makes of the caller asking.

    Admin-only: it reports the address our edge saw, which is not
    something to hand out publicly. See ClientIdentity for what the answer
    means and how to read it.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    peer = request.client.host if request.client else None
    key = login_throttle.client_key(forwarded_for, peer)
    return ClientIdentity(
        forwarded_for=forwarded_for,
        hops=[hop.strip() for hop in (forwarded_for or "").split(",") if hop.strip()],
        peer=peer,
        throttle_key=key,
        recent_failures=login_throttle.failure_count(key),
        retry_after_seconds=login_throttle.retry_after_seconds(key),
    )
