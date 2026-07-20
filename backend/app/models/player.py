from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, computed_field

EloTier = Literal["milk", "soju", "beer", "whisky", "highball", "vodka"]
DominantHand = Literal["left", "right"]


class PlayerBase(BaseModel):
    nickname: str
    line_id: str | None = None
    dominant_hand: DominantHand | None = None
    tiktok: str | None = None
    instagram: str | None = None


class PlayerCreate(PlayerBase):
    elo_score: int | None = None
    """Starting rating for a player who isn't a true beginner — defaults to
    elo_service.STARTING_SCORE (1000) when omitted."""


class PlayerUpdate(BaseModel):
    nickname: str | None = None
    line_id: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None
    dominant_hand: DominantHand | None = None
    tiktok: str | None = None
    instagram: str | None = None


class Player(PlayerBase):
    id: UUID
    avatar_url: str | None = None
    elo_score: int
    elo_level: EloTier
    is_active: bool
    created_at: datetime
    member_seq: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def member_code(self) -> str:
        """Display code e.g. "ND007" — derived from member_seq, not stored."""
        return f"ND{self.member_seq:03d}"


class PlayerStats(BaseModel):
    """Aggregated per-player stats for the Member List / Ranking views."""

    player: Player
    games: int
    wins: int
    draws: int
    losses: int
    points: int
    avg_points: float
    score_percent: float


class NemesisInfo(BaseModel):
    """The opponent this player has faced most often ("เทกันจัง")."""

    player: Player
    encounters: int
    wins: int
    losses: int
    draws: int


class PlayerProfile(BaseModel):
    """Single-player detail page — Member List stats plus their nemesis."""

    player: Player
    games: int
    wins: int
    draws: int
    losses: int
    points: int
    avg_points: float
    score_percent: float
    nemesis: NemesisInfo | None = None
    elo_rank: int
    total_ranked_players: int
    similar_players: list[Player] = []
