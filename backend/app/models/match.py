from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.player import Player

MatchType = Literal["single", "double"]
MatchStatus = Literal["in_progress", "completed"]
Winner = Literal["team1", "team2", "draw"]

SetScore = tuple[int, int]

TEAM_SIZE_BY_TYPE: dict[MatchType, int] = {"single": 1, "double": 2}


class MatchResultSubmit(BaseModel):
    """Admin submits the outcome directly — win/loss/draw, no set scores."""

    winner: Winner


class Match(BaseModel):
    id: UUID
    session_id: UUID
    type: MatchType
    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]
    sets: list[SetScore] | None = None
    winner: Winner | None = None
    status: MatchStatus
    created_at: datetime
    updated_at: datetime


class PlayerMatchStat(BaseModel):
    """A player's overall record, shown side-by-side with their match opponents."""

    player: Player
    games: int
    wins: int
    draws: int
    losses: int
    score_percent: float
    elo_rank: int


class MatchDetail(BaseModel):
    """Head-to-head detail view for a single match."""

    match: Match
    team1: list[PlayerMatchStat]
    team2: list[PlayerMatchStat]
    duration_minutes: float | None = None
