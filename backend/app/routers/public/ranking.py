from datetime import date as DateType
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import Player, PlayerStats
from app.services import record_service, stats_service

router = APIRouter(prefix="/api/ranking", tags=["public-ranking"])

RankingPeriod = Literal["day", "year", "all"]


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


def _play_dates(supabase: SupabaseDep) -> list[DateType]:
    """Every session date with at least one completed match, newest first."""
    session_ids = [row["session_id"] for row in record_service.completed_matches(supabase, "session_id")]
    if not session_ids:
        return []
    sessions_result = (
        supabase.table("sessions").select("id, date").in_("id", list(set(session_ids))).execute()
    )
    return stats_service.play_dates(session_ids, rows(sessions_result))  # type: ignore[arg-type]


@router.get("/days", response_model=list[DateType])
def get_play_dates(supabase: SupabaseDep) -> list[DateType]:
    """The days the daily ranking can be built for, newest first — every one
    is guaranteed to produce a non-empty leaderboard, so a date picker built
    from this list can't offer a day that turns out blank."""
    return _play_dates(supabase)


@router.get("", response_model=list[PlayerStats])
def get_ranking(
    supabase: SupabaseDep,
    period: RankingPeriod = Query(default="all"),
    date: DateType | None = Query(default=None),
) -> list[PlayerStats]:
    """`date` applies to period="day" only and is ignored otherwise. Omitting
    it on period="day" resolves to the most recent day that has matches
    rather than erroring, so the tab always opens on real data."""
    players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    players = [Player.model_validate(row) for row in rows(players_result)]

    records: dict[UUID, stats_service.PlayerRecord] = {}

    if period == "all":
        # Counted from the matches, the same as the members list, a profile
        # and the match history — see record_service.
        records = record_service.all_records(supabase)
    elif period == "day":
        # Scoped through sessions.date, not matches.created_at: a Friday
        # session running past midnight UTC would otherwise split across two
        # calendar days, and the club thinks in play-nights, not UTC dates.
        target = date or next(iter(_play_dates(supabase)), None)
        if target is None:
            return []
        sessions_result = (
            supabase.table("sessions").select("id").eq("date", target.isoformat()).execute()
        )
        session_ids = [row["id"] for row in rows(sessions_result)]
        if not session_ids:
            return []
        matches_result = (
            supabase.table("matches")
            .select("team1_player_ids, team2_player_ids, winner")
            .eq("status", "completed")
            .in_("session_id", session_ids)
            .execute()
        )
        records = stats_service.build_player_records(rows(matches_result))  # type: ignore[arg-type]
    elif period == "year":
        # Bounded to this year's matches at the query level (not fetched in
        # full then filtered in Python), and paged: a year of club nights is
        # already near PostgREST's 1000-row ceiling.
        year_start = datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
        records = stats_service.build_player_records(
            record_service.completed_matches(supabase, since=year_start)  # type: ignore[arg-type]
        )

    stats: list[PlayerStats] = []
    for player in players:
        record = records.get(player.id, stats_service.PlayerRecord())
        if record.games == 0:
            continue  # ranking only shows players who've played at least one match
        stats.append(_stats_from_record(player, record))

    stats.sort(key=lambda s: (s.points, s.score_percent), reverse=True)
    return stats
