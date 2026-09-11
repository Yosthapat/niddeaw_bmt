from datetime import date, datetime
from typing import Literal, Self
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
    status: Literal["queued", "in_progress"] = "in_progress"
    """"queued" lets an admin pre-build the next pairing — including
    players still mid-match — without starting it yet; promoted to
    in_progress only via the separate /matches/{id}/start action."""
    court: str | None = None

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


class MatchmakingEditRequest(BaseModel):
    """Amends an already-queued pairing in place. Deliberately has no
    `status` and no `session_id` — both are read off the match being
    edited, so an edit can never move a match to another session or start
    it; starting stays the separate /matches/{id}/start action.

    Team sizes aren't checked here: they depend on the match's own `type`,
    which only the router knows once it has fetched the row."""

    team1_player_ids: list[UUID]
    team2_player_ids: list[UUID]
    court: str | None = None

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
    court: str | None = None


class WaitingEntry(BaseModel):
    player_id: UUID
    queue_position: int
    estimated_wait_minutes: float


class MatchmakingQueueResponse(BaseModel):
    in_progress: list[QueueEntry]
    queued: list[QueueEntry] = []
    suggestions: list[PairingSuggestion]
    waiting: list[WaitingEntry]
    avg_match_duration_minutes: float
    locked_pairs: list[LockedPair] = []


class LiveQueueResponse(BaseModel):
    """Public, read-only view of the current session's queue — self-resolves
    the open session server-side (no session_id from the caller) and reports
    whether one exists at all.

    Carries `queued` (pairings an admin actually confirmed) where the admin
    view carries `suggestions` instead: suggestions are unconfirmed proposals
    that reshuffle on every poll, so showing them to members would keep
    promising matchups that never happen."""

    session_id: UUID | None
    session_date: date | None
    location: str | None
    in_progress: list[QueueEntry]
    queued: list[QueueEntry]
    waiting: list[WaitingEntry]
    avg_match_duration_minutes: float
