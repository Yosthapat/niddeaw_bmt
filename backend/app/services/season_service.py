"""Seasons, derived from session dates rather than stored.

A season is one calendar year. Season 1 is the year of the club's first
session, season 2 the year after, and so on — so the numbering is stable
once assigned and never shifts as history grows.

There is deliberately no `seasons` table. The alternative definition —
rolling 12-month windows anchored on the first session — produces
boundaries like "15 Mar 2026 – 14 Mar 2027" that nobody can hold in their
head, and would need a table to pin them. The cost of calendar years is
that season 1 is short if the club started mid-year; that's the trade
taken.

Years with no play still get a season number (the range is contiguous), so
a gap year can't renumber every season after it.
"""

from dataclasses import dataclass
from datetime import date as DateType
from datetime import datetime, timezone

from supabase import Client

from app.db_utils import rows


@dataclass(frozen=True)
class SeasonSpan:
    number: int
    year: int
    start_date: DateType
    end_date: DateType
    is_current: bool


def build_seasons(first_play_date: DateType | None, today: DateType) -> list[SeasonSpan]:
    """Every season from the club's first up to the one containing `today`,
    oldest first. No sessions at all means no seasons — not a season 1 that
    nothing happened in.

    If `today` somehow precedes the first session (a clock skew, or a
    back-dated session), the list still contains that first season but none
    is flagged current; callers pick a default rather than assuming one
    exists.
    """
    if first_play_date is None:
        return []
    first_year = first_play_date.year
    last_year = max(first_year, today.year)
    return [
        SeasonSpan(
            number=year - first_year + 1,
            year=year,
            start_date=DateType(year, 1, 1),
            end_date=DateType(year, 12, 31),
            is_current=year == today.year,
        )
        for year in range(first_year, last_year + 1)
    ]


def find_span(seasons: list[SeasonSpan], number: int) -> SeasonSpan | None:
    return next((season for season in seasons if season.number == number), None)


def fetch_seasons(supabase: Client) -> list[SeasonSpan]:
    """Reads only the earliest session date — the rest is arithmetic, so
    this costs one row no matter how much history the club has."""
    result = supabase.table("sessions").select("date").order("date").limit(1).execute()
    session_rows = rows(result)
    first_play_date = DateType.fromisoformat(session_rows[0]["date"]) if session_rows else None
    # UTC, matching the ranking endpoint's year bucketing — the club is in
    # one timezone, so this only ever differs for a few hours around new
    # year, and picking the same clock as everything else beats picking a
    # more "correct" one that disagrees with it.
    return build_seasons(first_play_date, datetime.now(timezone.utc).date())
