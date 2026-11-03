from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from app.models.admin import AdminContext
from app.models.line import LineContext
from app.security import ADMIN_ROLE, LINE_ROLE, decode_access_token
from app.supabase_client import get_supabase_client


def get_supabase() -> Client:
    return get_supabase_client()


SupabaseDep = Annotated[Client, Depends(get_supabase)]


def get_current_admin(authorization: Annotated[str | None, Header()] = None) -> AdminContext:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc

    # Only an admin's token opens an admin route. A member's LINE token is
    # signed with the same secret, so the role is what tells them apart.
    if payload.get("role") != ADMIN_ROLE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an admin token")
    try:
        admin_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token payload"
        ) from exc

    return AdminContext(admin_id=admin_id, role="admin")


AdminDep = Annotated[AdminContext, Depends(get_current_admin)]


def get_line_member(authorization: Annotated[str | None, Header()] = None) -> LineContext:
    """A member signed in on the /line page (POST /api/line/session)."""
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ต้องเข้าผ่าน LINE ก่อน")
    try:
        payload = decode_access_token(authorization.split(" ", 1)[1])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="เข้าผ่าน LINE ใหม่อีกครั้ง"
        ) from exc
    sub = payload.get("sub")
    if payload.get("role") != LINE_ROLE or not isinstance(sub, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="เข้าผ่าน LINE ใหม่อีกครั้ง")
    picture = payload.get("pic")
    return LineContext(
        line_user_id=sub,
        line_name=str(payload.get("name") or ""),
        line_picture=picture if isinstance(picture, str) else None,
    )


LineMemberDep = Annotated[LineContext, Depends(get_line_member)]
