from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.admin import AdminLoginRequest, AdminLoginResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest, supabase: SupabaseDep) -> AdminLoginResponse:
    result = (
        supabase.table("admins")
        .select("id, username, password_hash, role")
        .eq("username", payload.username)
        .limit(1)
        .execute()
    )
    admin_rows = rows(result)
    if not admin_rows or not verify_password(payload.password, admin_rows[0]["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )

    admin_row = admin_rows[0]
    token = create_access_token(admin_id=admin_row["id"], role=admin_row["role"])
    settings = get_settings()
    return AdminLoginResponse(access_token=token, expires_in_minutes=settings.jwt_expire_minutes)
