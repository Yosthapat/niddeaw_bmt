from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CheckinCreate(BaseModel):
    session_id: UUID
    player_id: UUID


class Checkin(BaseModel):
    id: UUID
    session_id: UUID
    player_id: UUID
    checkin_time: datetime
    checkout_time: datetime | None = None
    via: Literal["admin", "line"] = "admin"
    """Who checked them in: the admin at the door, or they did, through LINE."""
