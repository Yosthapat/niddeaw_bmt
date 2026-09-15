from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.admin import AdminLoginRequest, AdminLoginResponse
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
        .select("id, username, password_hash, role")
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
    token = create_access_token(admin_id=admin_row["id"], role=admin_row["role"])
    settings = get_settings()
    return AdminLoginResponse(access_token=token, expires_in_minutes=settings.jwt_expire_minutes)
