from typing import Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.models.match import TEAM_SIZE_BY_TYPE, MatchStatus, MatchType


class PairingSuggestion(BaseModel):
    group_no: int
    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]
    elo_balance_score: float
    fairness_penalty: float


class MatchmakingSuggestionResponse(BaseModel):
    suggestions: list[PairingSuggestion]
    waiting_player_ids: list[UUID]


class MatchmakingConfirmRequest(BaseModel):
    session_id: UUID
    type: MatchType
    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]

    @model_validator(mode="after")
    def _validate_team_sizes(self) -> Self:
        expected = TEAM_SIZE_BY_TYPE[self.type]
        if len(self.team1_player_ids) != expected or len(self.team2_player_ids) != expected:
            raise ValueError(f"match type '{self.type}' requires {expected} player(s) per team")
        return self

    @model_validator(mode="after")
    def _validate_no_duplicate_players(self) -> Self:
        all_ids = self.team1_player_ids + self.team2_player_ids
        if len(set(all_ids)) != len(all_ids):
            raise ValueError("a player cannot appear more than once across team1/team2")
        return self


class QueueEntry(BaseModel):
    match_id: UUID
    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]
    status: MatchStatus


class WaitingEntry(BaseModel):
    player_id: UUID
    queue_position: int
    estimated_wait_minutes: float


class MatchmakingQueueResponse(BaseModel):
    in_progress: list[QueueEntry]
    suggestions: list[PairingSuggestion]
    waiting: list[WaitingEntry]
    avg_match_duration_minutes: float
