from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.match import Match, MatchDetail, PlayerMatchStat
from app.models.player import Player
from app.services import stats_service

router = APIRouter(prefix="/api/matches", tags=["public-matches"])


@router.get("", response_model=list[Match])
def list_matches(
    supabase: SupabaseDep,
    session_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Match]:
    query = (
        supabase.table("matches")
        .select("*")
        .eq("status", "completed")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if session_id is not None:
        query = query.eq("session_id", str(session_id))
    result = query.execute()
    return [Match.model_validate(row) for row in rows(result)]


@router.get("/{match_id}/detail", response_model=MatchDetail)
def get_match_detail(match_id: UUID, supabase: SupabaseDep) -> MatchDetail:
    match_result = supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    match = Match.model_validate(match_rows[0])

    active_players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    players_by_id = {p.id: p for p in (Player.model_validate(row) for row in rows(active_players_result))}
    all_scores = [p.elo_score for p in players_by_id.values()]

    all_ids = match.team1_player_ids + match.team2_player_ids
    missing_ids = [pid for pid in all_ids if pid not in players_by_id]
    if missing_ids:
        extra_result = (
            supabase.table("players")
            .select("*")
            .in_("id", [str(pid) for pid in missing_ids])
            .execute()
        )
        for row in rows(extra_result):
            player = Player.model_validate(row)
            players_by_id[player.id] = player

    def build_stat(pid: UUID) -> PlayerMatchStat:
        player = players_by_id[pid]
        record = stats_service.PlayerRecord(
            games=player.games, wins=player.wins, draws=player.draws, losses=player.losses
        )
        return PlayerMatchStat(
            player=player,
            games=record.games,
            wins=record.wins,
            draws=record.draws,
            losses=record.losses,
            score_percent=record.score_percent,
            elo_rank=stats_service.elo_rank(player.elo_score, all_scores),
        )

    duration_minutes: float | None = None
    if match.status == "completed":
        duration_minutes = (match.updated_at - match.created_at).total_seconds() / 60

    return MatchDetail(
        match=match,
        team1=[build_stat(pid) for pid in match.team1_player_ids],
        team2=[build_stat(pid) for pid in match.team2_player_ids],
        duration_minutes=duration_minutes,
    )
