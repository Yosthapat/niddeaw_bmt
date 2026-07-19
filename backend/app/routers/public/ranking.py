from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Query

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import Player, PlayerStats
from app.services import stats_service

router = APIRouter(prefix="/api/ranking", tags=["public-ranking"])

RankingPeriod = Literal["year", "all"]


@router.get("", response_model=list[PlayerStats])
def get_ranking(
    supabase: SupabaseDep, period: RankingPeriod = Query(default="all")
) -> list[PlayerStats]:
    players_result = supabase.table("players").select("*").eq("is_active", True).execute()

    matches_query = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids, winner, created_at")
        .eq("status", "completed")
    )
    matches_result = matches_query.execute()

    match_rows = rows(matches_result)
    if period == "year":
        current_year = datetime.now(timezone.utc).year
        match_rows = [
            row
            for row in match_rows
            if datetime.fromisoformat(str(row["created_at"])).year == current_year
        ]

    records = stats_service.build_player_records(match_rows)  # type: ignore[arg-type]

    stats: list[PlayerStats] = []
    for row in rows(players_result):
        player = Player.model_validate(row)
        record = records.get(player.id, stats_service.PlayerRecord())
        if record.games == 0:
            continue  # ranking only shows players who've played at least one match
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
    return stats
