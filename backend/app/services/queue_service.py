"""I/O layer that assembles a session's live matchmaking queue.

Split out from the admin matchmaking router so the public /api/live
endpoint can build the same in-progress/suggestions/waiting view without
duplicating the Supabase query chain. Unlike matchmaking_service.py, these
functions do talk to Supabase directly.
"""

from datetime import datetime
from uuid import UUID

from postgrest.types import CountMethod
from supabase import Client

from app.db_utils import rows
from app.models.matchmaking import MatchmakingQueueResponse, PairingSuggestion, QueueEntry, WaitingEntry
from app.services import matchmaking_service

RECENT_MATCHES_FOR_DURATION_AVG = 10


def fetch_checked_in_players(
    supabase: Client, session_id: UUID, exclude_ids: set[UUID]
) -> list[matchmaking_service.CheckedInPlayer]:
    checkins_result = (
        supabase.table("checkins")
        .select("player_id")
        .eq("session_id", str(session_id))
        .is_("checkout_time", "null")
        .execute()
    )
    player_ids = [UUID(row["player_id"]) for row in rows(checkins_result)]
    player_ids = [pid for pid in player_ids if pid not in exclude_ids]
    if not player_ids:
        return []

    players_result = (
        supabase.table("players")
        .select("id, elo_score")
        .in_("id", [str(pid) for pid in player_ids])
        .execute()
    )
    return [
        matchmaking_service.CheckedInPlayer(player_id=UUID(row["id"]), elo_score=row["elo_score"])
        for row in rows(players_result)
    ]


def fetch_pairing_history(
    supabase: Client, session_id: UUID
) -> list[matchmaking_service.PairHistoryEntry]:
    result = (
        supabase.table("pairing_history")
        .select("player_a_id, player_b_id, relation, round_no")
        .eq("session_id", str(session_id))
        .execute()
    )
    return [
        matchmaking_service.PairHistoryEntry(
            player_a_id=UUID(row["player_a_id"]),
            player_b_id=UUID(row["player_b_id"]),
            relation=row["relation"],
            round_no=row["round_no"],
        )
        for row in rows(result)
    ]


def players_in_progress(supabase: Client, session_id: UUID) -> set[UUID]:
    result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids")
        .eq("session_id", str(session_id))
        .eq("status", "in_progress")
        .execute()
    )
    ids: set[UUID] = set()
    for row in rows(result):
        ids.update(UUID(pid) for pid in row["team1_player_ids"])
        ids.update(UUID(pid) for pid in row["team2_player_ids"])
    return ids


def current_round_no(supabase: Client, session_id: UUID) -> int:
    result = (
        supabase.table("matches")
        .select("id", count=CountMethod.exact)
        .eq("session_id", str(session_id))
        .execute()
    )
    return (result.count or 0) + 1


def build_suggestions(
    supabase: Client, session_id: UUID
) -> tuple[list[PairingSuggestion], list[UUID]]:
    in_progress_ids = players_in_progress(supabase, session_id)
    checked_in = fetch_checked_in_players(supabase, session_id, in_progress_ids)
    history = fetch_pairing_history(supabase, session_id)
    current_round = current_round_no(supabase, session_id)

    splits, waiting = matchmaking_service.suggest_doubles_pairings(checked_in, history, current_round)
    suggestions = [
        PairingSuggestion(
            group_no=i + 1,
            team1_player_ids=list(split.team1),
            team2_player_ids=list(split.team2),
            elo_balance_score=split.elo_balance_score,
            fairness_penalty=split.fairness_penalty,
        )
        for i, split in enumerate(splits)
    ]
    return suggestions, waiting


def build_queue(supabase: Client, session_id: UUID) -> MatchmakingQueueResponse:
    in_progress_result = (
        supabase.table("matches")
        .select("id, team1_player_ids, team2_player_ids, status")
        .eq("session_id", str(session_id))
        .eq("status", "in_progress")
        .execute()
    )
    in_progress = [
        QueueEntry(
            match_id=UUID(row["id"]),
            team1_player_ids=[UUID(pid) for pid in row["team1_player_ids"]],
            team2_player_ids=[UUID(pid) for pid in row["team2_player_ids"]],
            status=row["status"],
        )
        for row in rows(in_progress_result)
    ]

    suggestions, waiting_ids = build_suggestions(supabase, session_id)

    recent_result = (
        supabase.table("matches")
        .select("created_at, updated_at")
        .eq("session_id", str(session_id))
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(RECENT_MATCHES_FOR_DURATION_AVG)
        .execute()
    )
    durations = [
        (
            datetime.fromisoformat(str(row["updated_at"]))
            - datetime.fromisoformat(str(row["created_at"]))
        ).total_seconds()
        / 60
        for row in rows(recent_result)
        if row.get("updated_at")
    ]
    avg_duration = (
        sum(durations) / len(durations)
        if durations
        else matchmaking_service.DEFAULT_MATCH_DURATION_MINUTES
    )

    waiting = [
        WaitingEntry(
            player_id=pid,
            queue_position=i + 1,
            estimated_wait_minutes=matchmaking_service.estimate_wait_minutes(i + 1, durations),
        )
        for i, pid in enumerate(waiting_ids)
    ]

    return MatchmakingQueueResponse(
        in_progress=in_progress,
        suggestions=suggestions,
        waiting=waiting,
        avg_match_duration_minutes=avg_duration,
    )
