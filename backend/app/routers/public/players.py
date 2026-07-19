from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import Player, PlayerStats
from app.services import stats_service

router = APIRouter(prefix="/api/players", tags=["public-players"])


@router.get("", response_model=list[PlayerStats])
def list_players(supabase: SupabaseDep) -> list[PlayerStats]:
    players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    matches_result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids, winner")
        .eq("status", "completed")
        .execute()
    )
    records = stats_service.build_player_records(rows(matches_result))  # type: ignore[arg-type]

    stats: list[PlayerStats] = []
    for row in rows(players_result):
        player = Player.model_validate(row)
        record = records.get(player.id, stats_service.PlayerRecord())
        stats.append(
            PlayerStats(
                player=player,
                games=record.games,
                wins=record.wins,
                draws=record.draws,
                losses=record.losses,
                points=record.points,
                avg_points=record.avg_points,
                score_percent=record.score_percent,
            )
        )
    return stats


@router.get("/{player_id}", response_model=Player)
def get_player(player_id: UUID, supabase: SupabaseDep) -> Player:
    result = supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute()
    player_rows = rows(result)
    if not player_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(player_rows[0])
