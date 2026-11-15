from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PassPerson(BaseModel):
    player_id: UUID
    nickname: str
    avatar_url: str | None = None


class LinePass(BaseModel):
    """A member's own Niddeaw Pass, as the /line page shows it."""

    price: int
    days: int
    balance: int
    eligible: bool
    """Holds a credit card (a 1,000 pack or more bought through LINE)."""
    ends_at: datetime | None = None
    """When their pass ends; None when none runs."""
    season_points: float
    season_year: int
    max_blocks: int
    checked_in: bool
    """In tonight: blocks can be chosen."""
    blocks: list[PassPerson] = []
    candidates: list[PassPerson] = []
    """Who else is in tonight, to choose from."""


class PassBlockIn(BaseModel):
    player_id: UUID
