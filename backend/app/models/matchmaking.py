from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.models.match import TEAM_SIZE_BY_TYPE, MatchStatus, MatchType


class LockedPairCreate(BaseModel):
    session_id: UUID
    player_a_id: UUID
    player_b_id: UUID

    @model_validator(mode="after")
    def _validate_distinct(self) -> Self:
        if self.player_a_id == self.player_b_id:
            raise ValueError("a player cannot be locked with themselves")
        return self


class LockedPair(BaseModel):
    id: UUID
    session_id: UUID
    player_a_id: UUID
    player_b_id: UUID
    created_at: datetime


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
    locked_pairs: list[LockedPair] = []


class LiveQueueResponse(BaseModel):
    """Public, read-only view of the current session's queue — same shape as
    MatchmakingQueueResponse but self-resolves the open session server-side
    (no session_id from the caller) and reports whether one exists at all."""

    session_id: UUID | None
    session_date: date | None
    location: str | None
    in_progress: list[QueueEntry]
    suggestions: list[PairingSuggestion]
    waiting: list[WaitingEntry]
    avg_match_duration_minutes: float
