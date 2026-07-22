from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.match import Match, MatchResultSubmit
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


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_match(match_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Cancels a mis-paired or no-longer-needed match — only while it's still
    in_progress, so a completed match's result/ELO history can't be erased
    by mistake. pairing_history rows cascade-delete with the match."""
    match_result = supabase.table("matches").select("status").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match_rows[0]["status"] != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an in-progress match can be cancelled",
        )
    supabase.table("matches").delete().eq("id", str(match_id)).execute()


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
    winner = payload.winner

    all_ids = team1_ids + team2_ids
    players_result = (
        supabase.table("players")
        .select("id, elo_score, games, wins, draws, losses")
        .in_("id", [str(pid) for pid in all_ids])
        .execute()
    )
    players_by_id = {UUID(row["id"]): row for row in rows(players_result)}
    scores_by_id: dict[UUID, int] = {pid: row["elo_score"] for pid, row in players_by_id.items()}

    delta_team1, delta_team2 = elo_service.compute_deltas(
        [scores_by_id[pid] for pid in team1_ids],
        [scores_by_id[pid] for pid in team2_ids],
        winner,
    )

    def _apply_result(pid: UUID, delta: int, outcome: str) -> None:
        row = players_by_id[pid]
        new_score = elo_service.apply_delta(row["elo_score"], delta)
        supabase.table("players").update(
            {
                "elo_score": new_score,
                "elo_level": elo_service.get_tier(new_score),
                "games": row["games"] + 1,
                "wins": row["wins"] + (1 if outcome == "win" else 0),
                "draws": row["draws"] + (1 if outcome == "draw" else 0),
                "losses": row["losses"] + (1 if outcome == "loss" else 0),
            }
        ).eq("id", str(pid)).execute()

    team1_outcome = "win" if winner == "team1" else "draw" if winner == "draw" else "loss"
    team2_outcome = "win" if winner == "team2" else "draw" if winner == "draw" else "loss"
    for pid in team1_ids:
        _apply_result(pid, delta_team1, team1_outcome)
    for pid in team2_ids:
        _apply_result(pid, delta_team2, team2_outcome)

    updated = (
        supabase.table("matches")
        .update(
            {
                "winner": winner,
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(match_id))
        .execute()
    )
    return Match.model_validate(rows(updated)[0])
