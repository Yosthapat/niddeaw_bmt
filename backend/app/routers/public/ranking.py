from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Query

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import Player, PlayerStats
from app.services import stats_service

router = APIRouter(prefix="/api/ranking", tags=["public-ranking"])

RankingPeriod = Literal["year", "all"]


def _stats_from_record(player: Player, record: stats_service.PlayerRecord) -> PlayerStats:
    return PlayerStats(
        player=player,
        games=record.games,
        wins=record.wins,
        draws=record.draws,
        losses=record.losses,
        points=record.points,
        avg_points=record.avg_points,
        score_percent=record.score_percent,
    )


@router.get("", response_model=list[PlayerStats])
def get_ranking(
    supabase: SupabaseDep, period: RankingPeriod = Query(default="all")
) -> list[PlayerStats]:
    players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    players = [Player.model_validate(row) for row in rows(players_result)]

    stats: list[PlayerStats] = []
    if period == "all":
        # Denormalized totals — no match-history scan needed.
        for player in players:
            record = stats_service.PlayerRecord(
                games=player.games, wins=player.wins, draws=player.draws, losses=player.losses
            )
            if record.games == 0:
                continue  # ranking only shows players who've played at least one match
            stats.append(_stats_from_record(player, record))
    else:
        # "This year" isn't denormalized, but is bounded to this year's
        # matches at the query level (not fetched in full then filtered in
        # Python) so it stays cheap regardless of the club's total history.
        year_start = datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
        matches_result = (
            supabase.table("matches")
            .select("team1_player_ids, team2_player_ids, winner, created_at")
            .eq("status", "completed")
            .gte("created_at", year_start.isoformat())
            .execute()
        )
        records = stats_service.build_player_records(rows(matches_result))  # type: ignore[arg-type]
        for player in players:
            record = records.get(player.id, stats_service.PlayerRecord())
            if record.games == 0:
                continue
            stats.append(_stats_from_record(player, record))

    stats.sort(key=lambda s: (s.points, s.score_percent), reverse=True)
    return stats
