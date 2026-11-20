from datetime import date, datetime
from typing import Literal
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
    max_blocks: int
    checked_in: bool
    """In tonight: blocks can be chosen."""
    blocks: list[PassPerson] = []
    candidates: list[PassPerson] = []
    """Who else is in tonight, to choose from."""
    frame: str | None = None
    card: str | None = None
    """The look they chose. It shows only while open below."""
    frames_open: list[str] = []
    cards_open: list[str] = []
    """What they may wear now: the pass looks while a pass runs, and the
    loyal ones they have earned."""
    streak: int = 0
    """Passes in a row up to now; 0 when none runs."""
    best_streak: int = 0


class PassBlockIn(BaseModel):
    player_id: UUID


Frame = Literal["gold", "neon", "crown", "moon", "king", "legend"]
CardFace = Literal["foil", "diamond"]


class PassLook(BaseModel):
    """What shows of a member's pass to everyone: the frame round their
    picture and the face of their profile card."""

    frame: Frame | None = None
    card: CardFace | None = None


class PassStyleIn(BaseModel):
    frame: Frame | None = None
    card: CardFace | None = None


class EloPoint(BaseModel):
    at: datetime
    elo: int
    """Their rating after this match."""
    delta: int = 0
    """What this match changed it by."""
    upset: bool = False
    """A win they had less than even odds of."""


class PassMate(BaseModel):
    player: PassPerson
    wins: int
    games: int


class FormBucket(BaseModel):
    bucket: Literal["early", "mid", "late"]
    wins: int
    games: int


class PassStats(BaseModel):
    """Only the holder's own numbers, in LINE, while their pass runs."""

    elo: int
    series: list[EloPoint]
    partner: PassMate | None = None
    """The teammate they win most with (3 games or more together)."""
    rival: PassMate | None = None
    """The opponent they beat least (3 games or more)."""
    form: list[FormBucket]
    last: list[Literal["W", "L", "D"]]
    best_streak: int
    games: int


class PassUpset(BaseModel):
    rivals: list[PassPerson]
    odds: float


class PassNight(BaseModel):
    """Their last night with a result, for the picture they can share."""

    date: date
    nickname: str
    frame: str | None = None
    games: int
    wins: int
    draws: int
    elo_before: int
    elo_after: int
    upset: PassUpset | None = None
    partner: PassMate | None = None


class PassSale(BaseModel):
    """One pass bought, for the admin's list."""

    id: UUID
    player_id: UUID
    nickname: str
    member_code: str
    avatar_url: str | None = None
    starts_at: datetime
    ends_at: datetime
    credits: int
    created_at: datetime
    running: bool
    """This pass is the one running now."""
    in_a_row: int
    """Which pass this is in the member's unbroken run (1 = a fresh start)."""


class PassDay(BaseModel):
    date: date
    count: int
    credits: int


class PassAdmin(BaseModel):
    """Niddeaw Pass for the admin: who bought, who holds one now, and what
    was spent on it. Paid with club credit, whose cash was already counted
    when it was topped up, so none of this is income on top of that."""

    holders: int
    """Members with a pass running now."""
    month_count: int
    month_credits: int
    """Bought this (Bangkok) month."""
    total_count: int
    total_credits: int
    latest_at: datetime | None = None
    """When the newest pass was bought: the dashboard's "new" dot."""
    sales: list[PassSale]
    """Newest first."""
    daily: list[PassDay]
    """Newest first, Bangkok days."""
