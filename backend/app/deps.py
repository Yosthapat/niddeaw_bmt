from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from app.models.admin import AdminContext
from app.security import decode_access_token
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

    try:
        admin_id = UUID(payload["sub"])
        role = payload["role"]
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token payload"
        ) from exc

    return AdminContext(admin_id=admin_id, role=role)


AdminDep = Annotated[AdminContext, Depends(get_current_admin)]
