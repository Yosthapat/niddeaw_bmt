from datetime import date

from app.services import season_service


def test_no_sessions_means_no_seasons() -> None:
    # Not "season 1 with nothing in it" — a club that has never played has
    # no seasons to browse, and the profile page hides the selector.
    assert season_service.build_seasons(None, date(2026, 9, 13)) == []


def test_first_season_spans_the_calendar_year_of_the_first_session() -> None:
    seasons = season_service.build_seasons(date(2026, 3, 15), date(2026, 9, 13))
    assert len(seasons) == 1
    season = seasons[0]
    assert season.number == 1
    assert season.year == 2026
    # Starts 1 Jan, not on the first session — a season is a calendar year.
    assert season.start_date == date(2026, 1, 1)
    assert season.end_date == date(2026, 12, 31)
    assert season.is_current is True


def test_seasons_run_from_first_year_to_current_year_oldest_first() -> None:
    seasons = season_service.build_seasons(date(2024, 11, 1), date(2026, 9, 13))
    assert [(s.number, s.year) for s in seasons] == [(1, 2024), (2, 2025), (3, 2026)]
    assert [s.is_current for s in seasons] == [False, False, True]


def test_a_year_without_play_still_takes_a_season_number() -> None:
    # Numbering is by calendar year, not by "years that had matches", so a
    # quiet year can't renumber every season after it.
    seasons = season_service.build_seasons(date(2024, 5, 1), date(2027, 1, 2))
    assert [(s.number, s.year) for s in seasons] == [
        (1, 2024),
        (2, 2025),
        (3, 2026),
        (4, 2027),
    ]


def test_today_before_the_first_session_still_yields_that_season() -> None:
    # Back-dated session or a skewed clock: the season exists but nothing is
    # flagged current, so callers must pick a default rather than assume one.
    seasons = season_service.build_seasons(date(2027, 2, 1), date(2026, 9, 13))
    assert [(s.number, s.year) for s in seasons] == [(1, 2027)]
    assert all(not s.is_current for s in seasons)


def test_find_span_matches_by_season_number() -> None:
    seasons = season_service.build_seasons(date(2024, 11, 1), date(2026, 9, 13))
    span = season_service.find_span(seasons, 2)
    assert span is not None
    assert span.year == 2025
    assert span.start_date == date(2025, 1, 1)
    assert span.end_date == date(2025, 12, 31)


def test_find_span_returns_none_past_the_last_season() -> None:
    seasons = season_service.build_seasons(date(2026, 1, 1), date(2026, 9, 13))
    assert season_service.find_span(seasons, 9) is None
    assert season_service.find_span([], 1) is None
