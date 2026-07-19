from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

AdminRole = Literal["admin"]


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_minutes: int


class Admin(BaseModel):
    id: UUID
    username: str
    role: AdminRole
    created_at: datetime


class AdminContext(BaseModel):
    """Decoded + verified JWT identity, injected into admin-protected routes."""

    admin_id: UUID
    role: AdminRole
