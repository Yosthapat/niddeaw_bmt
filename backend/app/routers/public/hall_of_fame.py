"""Hall of Fame: all-time top players by ranking points (min. 5 games played
to qualify, so a single lucky win doesn't top the board). Not specified in
further detail by the original bmbad.com clone target, so this is a
reasonable, documented interpretation for Phase 1."""

from fastapi import APIRouter, Query

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import Player, PlayerStats
from app.services import stats_service

router = APIRouter(prefix="/api/hall-of-fame", tags=["public-hall-of-fame"])

MIN_GAMES_TO_QUALIFY = 5


@router.get("", response_model=list[PlayerStats])
def get_hall_of_fame(
    supabase: SupabaseDep, limit: int = Query(default=10, le=50)
) -> list[PlayerStats]:
    players_result = supabase.table("players").select("*").execute()
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
        if record.games < MIN_GAMES_TO_QUALIFY:
            continue
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

    stats.sort(key=lambda s: (s.points, s.score_percent), reverse=True)
    return stats[:limit]
