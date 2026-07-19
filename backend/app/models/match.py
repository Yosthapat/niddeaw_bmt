from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, model_validator

MatchType = Literal["single", "double"]
MatchStatus = Literal["in_progress", "completed"]
Winner = Literal["team1", "team2", "draw"]

SetScore = tuple[int, int]

_TEAM_SIZE_BY_TYPE: dict[MatchType, int] = {"single": 1, "double": 2}


class MatchCreate(BaseModel):
    session_id: UUID
    type: MatchType
    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]

    @model_validator(mode="after")
    def _validate_team_sizes(self) -> Self:
        expected = _TEAM_SIZE_BY_TYPE[self.type]
        if len(self.team1_player_ids) != expected or len(self.team2_player_ids) != expected:
            raise ValueError(f"match type '{self.type}' requires {expected} player(s) per team")
        return self


class MatchResultSubmit(BaseModel):
    """Admin submits raw set scores; winner is always derived server-side."""

    sets: list[SetScore]


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
