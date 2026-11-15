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
    # The two separate rights (0046_tournament.sql). A token issued before
    # they existed carries neither claim and reads as the club only, which
    # is what every admin had then.
    club_access: bool = True
    tournament_access: bool = False


class AdminMe(BaseModel):
    """Who is signed in, for the admin screens to choose which side to show."""

    id: UUID
    username: str
    club_access: bool
    tournament_access: bool
