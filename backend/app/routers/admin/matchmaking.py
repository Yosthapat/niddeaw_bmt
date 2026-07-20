from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.match import Match, MatchResultSubmit, Winner
from app.models.matchmaking import MatchmakingConfirmRequest, MatchmakingQueueResponse, MatchmakingSuggestionResponse
from app.services import elo_service, matchmaking_service, queue_service

router = APIRouter(prefix="/api/admin/matchmaking", tags=["admin-matchmaking"])


@router.get("/suggest", response_model=MatchmakingSuggestionResponse)
def suggest(
    session_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> MatchmakingSuggestionResponse:
    suggestions, waiting = queue_service.build_suggestions(supabase, session_id)
    return MatchmakingSuggestionResponse(suggestions=suggestions, waiting_player_ids=waiting)


@router.get("/queue", response_model=MatchmakingQueueResponse)
def queue(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> MatchmakingQueueResponse:
    return queue_service.build_queue(supabase, session_id)


@router.post("/confirm", response_model=Match, status_code=status.HTTP_201_CREATED)
def confirm(payload: MatchmakingConfirmRequest, supabase: SupabaseDep, admin: AdminDep) -> Match:
    round_no = queue_service.current_round_no(supabase, payload.session_id)
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
