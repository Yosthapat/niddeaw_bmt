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
    via: Literal["admin", "line", "gps"] = "admin"
    """Who checked them in: the admin at the door, or they did, through LINE."""
    paused_at: datetime | None = None
    """Set while they rest: still in for the night, left out of pairings."""


class CheckinPause(BaseModel):
    """Which member, on which night, to rest or bring back."""

    session_id: UUID
    player_id: UUID
