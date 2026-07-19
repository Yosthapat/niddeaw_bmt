from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from postgrest.types import CountMethod

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.match import Match, MatchResultSubmit, Winner
from app.models.matchmaking import (
    MatchmakingConfirmRequest,
    MatchmakingQueueResponse,
    MatchmakingSuggestionResponse,
    PairingSuggestion,
    QueueEntry,
    WaitingEntry,
)
from app.services import elo_service, matchmaking_service

router = APIRouter(prefix="/api/admin/matchmaking", tags=["admin-matchmaking"])

RECENT_MATCHES_FOR_DURATION_AVG = 10


def _fetch_checked_in_players(
    supabase: SupabaseDep, session_id: UUID, exclude_ids: set[UUID]
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


def _fetch_pairing_history(
    supabase: SupabaseDep, session_id: UUID
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


def _players_in_progress(supabase: SupabaseDep, session_id: UUID) -> set[UUID]:
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


def _current_round_no(supabase: SupabaseDep, session_id: UUID) -> int:
    result = (
        supabase.table("matches")
        .select("id", count=CountMethod.exact)
        .eq("session_id", str(session_id))
        .execute()
    )
    return (result.count or 0) + 1


def _build_suggestions(
    supabase: SupabaseDep, session_id: UUID
) -> tuple[list[PairingSuggestion], list[UUID]]:
    in_progress_ids = _players_in_progress(supabase, session_id)
    checked_in = _fetch_checked_in_players(supabase, session_id, in_progress_ids)
    history = _fetch_pairing_history(supabase, session_id)
    current_round = _current_round_no(supabase, session_id)

    splits, waiting = matchmaking_service.suggest_doubles_pairings(
        checked_in, history, current_round
    )
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


@router.get("/suggest", response_model=MatchmakingSuggestionResponse)
def suggest(
    session_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> MatchmakingSuggestionResponse:
    suggestions, waiting = _build_suggestions(supabase, session_id)
    return MatchmakingSuggestionResponse(suggestions=suggestions, waiting_player_ids=waiting)


@router.get("/queue", response_model=MatchmakingQueueResponse)
def queue(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> MatchmakingQueueResponse:
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

    suggestions, waiting_ids = _build_suggestions(supabase, session_id)

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


@router.post("/confirm", response_model=Match, status_code=status.HTTP_201_CREATED)
def confirm(payload: MatchmakingConfirmRequest, supabase: SupabaseDep, admin: AdminDep) -> Match:
    round_no = _current_round_no(supabase, payload.session_id)
    now = datetime.now(timezone.utc).isoformat()

    match_row = {
        "session_id": str(payload.session_id),
        "type": payload.type,
        "team1_player_ids": [str(pid) for pid in payload.team1_player_ids],
        "team2_player_ids": [str(pid) for pid in payload.team2_player_ids],
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
    }
    match_result = supabase.table("matches").insert(match_row).execute()
    match_result_rows = rows(match_result)
    match_id = match_result_rows[0]["id"]

    history_rows: list[dict[str, Any]] = matchmaking_service.build_pairing_history_rows(
        tuple(payload.team1_player_ids), tuple(payload.team2_player_ids), round_no
    )
    for row in history_rows:
        row["session_id"] = str(payload.session_id)
        row["match_id"] = match_id
    if history_rows:
        supabase.table("pairing_history").insert(history_rows).execute()

    return Match.model_validate(match_result_rows[0])


@router.post("/matches/{match_id}/result", response_model=Match)
def submit_result(
    match_id: UUID, payload: MatchResultSubmit, supabase: SupabaseDep, admin: AdminDep
) -> Match:
    match_result = supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    match_row = match_rows[0]

    team1_ids = [UUID(pid) for pid in match_row["team1_player_ids"]]
    team2_ids = [UUID(pid) for pid in match_row["team2_player_ids"]]

    sets_won_team1 = sum(1 for s1, s2 in payload.sets if s1 > s2)
    sets_won_team2 = sum(1 for s1, s2 in payload.sets if s2 > s1)
    winner: Winner
    if sets_won_team1 > sets_won_team2:
        winner = "team1"
    elif sets_won_team2 > sets_won_team1:
        winner = "team2"
    else:
        winner = "draw"

    all_ids = team1_ids + team2_ids
    players_result = (
        supabase.table("players")
        .select("id, elo_score")
        .in_("id", [str(pid) for pid in all_ids])
        .execute()
    )
    scores_by_id: dict[UUID, int] = {
        UUID(row["id"]): row["elo_score"] for row in rows(players_result)
    }

    delta_team1, delta_team2 = elo_service.compute_deltas(
        [scores_by_id[pid] for pid in team1_ids],
        [scores_by_id[pid] for pid in team2_ids],
        winner,
    )

    for pid in team1_ids:
        new_score = elo_service.apply_delta(scores_by_id[pid], delta_team1)
        supabase.table("players").update(
            {"elo_score": new_score, "elo_level": elo_service.get_tier(new_score)}
        ).eq("id", str(pid)).execute()
    for pid in team2_ids:
        new_score = elo_service.apply_delta(scores_by_id[pid], delta_team2)
        supabase.table("players").update(
            {"elo_score": new_score, "elo_level": elo_service.get_tier(new_score)}
        ).eq("id", str(pid)).execute()

    updated = (
        supabase.table("matches")
        .update(
            {
                "sets": [list(s) for s in payload.sets],
                "winner": winner,
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(match_id))
        .execute()
    )
    return Match.model_validate(rows(updated)[0])
