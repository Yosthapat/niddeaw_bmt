from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.session import Session, SessionCreate, SessionUpdate
from app.services import elo_service

router = APIRouter(prefix="/api/admin/sessions", tags=["admin-sessions"])

# A busy session can involve the whole roster, and each player is a separate
# Supabase round-trip — cap the fan-out instead of opening one connection
# per player.
MAX_STAT_UPDATE_WORKERS = 8


@router.get("", response_model=list[Session])
def list_sessions(supabase: SupabaseDep, admin: AdminDep) -> list[Session]:
    result = supabase.table("sessions").select("*").order("date", desc=True).execute()
    return [Session.model_validate(row) for row in rows(result)]


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, supabase: SupabaseDep, admin: AdminDep) -> Session:
    row = {**payload.model_dump(mode="json"), "status": "open", "created_by": str(admin.admin_id)}
    result = supabase.table("sessions").insert(row).execute()
    return Session.model_validate(rows(result)[0])


@router.patch("/{session_id}", response_model=Session)
def update_session(
    session_id: UUID, payload: SessionUpdate, supabase: SupabaseDep, admin: AdminDep
) -> Session:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = supabase.table("sessions").update(updates).eq("id", str(session_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Session.model_validate(result_rows[0])


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Permanently deletes a session — e.g. it was created by mistake, or a
    test session. Also undoes any elo_score/games/wins/draws/losses this
    session's completed matches applied to players, so a deleted session
    doesn't leave stats permanently skewed (matches recorded before
    elo_delta_team1/2 existed can't be undone and are left as-is).
    checkins/matches/billings/pairing_history all reference sessions with
    ON DELETE CASCADE, so the rows themselves are removed automatically."""
    # Read the matches first (the cascade takes them with the session), but
    # only reverse *after* the delete succeeds: the DELETE is the gate that
    # exactly one caller can pass, so a retry or two concurrent deletes can't
    # apply the reversal twice, and a failed delete can't leave stats docked
    # for a session that still exists.
    completed_matches = _completed_matches(session_id, supabase)

    result = supabase.table("sessions").delete().eq("id", str(session_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _reverse_match_stats(completed_matches, supabase)


def _completed_matches(session_id: UUID, supabase: Client) -> list[dict[str, Any]]:
    result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids, winner, elo_delta_team1, elo_delta_team2")
        .eq("session_id", str(session_id))
        .eq("status", "completed")
        .execute()
    )
    return rows(result)


def _reverse_match_stats(completed_matches: list[dict[str, Any]], supabase: Client) -> None:
    if not completed_matches:
        return

    all_ids = {
        UUID(pid)
        for match in completed_matches
        for pid in match["team1_player_ids"] + match["team2_player_ids"]
    }
    players_result = (
        supabase.table("players")
        .select("id, elo_score, games, wins, draws, losses")
        .in_("id", [str(pid) for pid in all_ids])
        .execute()
    )
    players_by_id = {UUID(row["id"]): row for row in rows(players_result)}
    if not players_by_id:
        return
    reversed_stats = elo_service.reverse_match_results(completed_matches, players_by_id)  # type: ignore[arg-type]

    def _apply_reversal(pid: UUID) -> None:
        stats = reversed_stats[pid]
        supabase.table("players").update(
            {
                "elo_score": stats["elo_score"],
                "elo_level": elo_service.get_tier(stats["elo_score"]),
                "games": stats["games"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
            }
        ).eq("id", str(pid)).execute()

    # One .update() per player, each to a different row — fully independent,
    # so run them concurrently instead of paying for N sequential Supabase
    # round-trips.
    with ThreadPoolExecutor(max_workers=min(len(players_by_id), MAX_STAT_UPDATE_WORKERS)) as pool:
        futures = [pool.submit(_apply_reversal, pid) for pid in players_by_id]
        for future in futures:
            future.result()
