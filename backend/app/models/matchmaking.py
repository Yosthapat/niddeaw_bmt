from uuid import UUID

from pydantic import BaseModel

from app.models.match import MatchStatus, MatchType


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
