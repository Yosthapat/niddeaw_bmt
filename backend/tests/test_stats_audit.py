"""Checking a profile's record against the matches it came from.

The numbers on a profile are counters on the player's own row, not a count
of match rows, so the two can disagree — and when they do, the matches are
the truth. These tests are about catching that disagreement, and about the
breakdown that tells a real drift apart from a profile counting the club's
whole history while somebody counts one night.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.services import stats_audit
from tests.conftest import FakeSupabase

P1 = str(uuid4())
P2 = str(uuid4())
P3 = str(uuid4())
P4 = str(uuid4())
NIGHT1 = str(uuid4())
NIGHT2 = str(uuid4())


class FakeTable:
    """Enough PostgREST to aggregate against: the filters here decide the
    answer, so a fake that ignored them would be testing nothing."""

    def __init__(self, rows: list[dict[str, Any]], updates: list[tuple[str, dict[str, Any]]]):
        self._rows = rows
        self._updates = updates
        self._filters: list[tuple[str, Any]] = []
        self._range: tuple[int, int] | None = None
        self._payload: dict[str, Any] | None = None

    def select(self, *_: Any, **__: Any) -> FakeTable:
        return self

    def order(self, *_: Any, **__: Any) -> FakeTable:
        return self

    def eq(self, column: str, value: Any) -> FakeTable:
        self._filters.append((column, lambda v, value=value: str(v) == str(value)))
        return self

    def in_(self, column: str, values: list[Any]) -> FakeTable:
        wanted = {str(v) for v in values}
        self._filters.append((column, lambda v, wanted=wanted: str(v) in wanted))
        return self

    def ilike(self, column: str, pattern: str) -> FakeTable:
        wanted = pattern.lower()
        self._filters.append((column, lambda v: str(v).lower() == wanted))
        return self

    def range(self, start: int, end: int) -> FakeTable:
        self._range = (start, end)
        return self

    def update(self, payload: dict[str, Any]) -> FakeTable:
        self._payload = payload
        return self

    def _matching(self) -> list[dict[str, Any]]:
        out = self._rows
        for column, predicate in self._filters:
            out = [row for row in out if predicate(row.get(column))]
        return out

    def execute(self) -> Any:
        matching = self._matching()
        if self._payload is not None:
            for row in matching:
                row.update(self._payload)
                self._updates.append((str(row.get("id")), dict(self._payload)))
            return type("R", (), {"data": matching})()
        if self._range is not None:
            start, end = self._range
            matching = matching[start : end + 1]
        return type("R", (), {"data": matching})()


class FakeDb:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def table(self, name: str) -> FakeTable:
        return FakeTable(self.tables.setdefault(name, []), self.updates)


def player(
    pid: str,
    nickname: str,
    *,
    games: int = 0,
    wins: int = 0,
    draws: int = 0,
    losses: int = 0,
    active: bool = True,
) -> dict[str, Any]:
    return {
        "id": pid,
        "nickname": nickname,
        "games": games,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "is_active": active,
    }


def match(
    *,
    team1: list[str],
    team2: list[str],
    winner: str = "team1",
    status: str = "completed",
    session: str = NIGHT1,
    at: str = "2026-10-01T10:00:00+00:00",
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "team1_player_ids": team1,
        "team2_player_ids": team2,
        "winner": winner,
        "status": status,
        "session_id": session,
        "created_at": at,
    }


def club(players: list[dict[str, Any]], matches: list[dict[str, Any]]) -> FakeDb:
    return FakeDb({"players": players, "matches": matches})


# --- what a clean club looks like ----------------------------------------


def test_a_club_whose_counters_add_up_reports_nobody() -> None:
    db = club(
        [player(P1, "Ball", games=1, wins=1), player(P2, "Aekk", games=1, losses=1)],
        [match(team1=[P1], team2=[P2])],
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert report.rows == []
    assert (report.players_checked, report.matches_counted) == (2, 1)


# --- the drift this exists to find ---------------------------------------


def test_a_profile_claiming_more_games_than_were_played_is_reported() -> None:
    """The reported case: ten on the profile, seven in the match history."""
    db = club(
        [player(P1, "Aekk", games=10, wins=10)],
        [match(team1=[P1], team2=[P2]) for _ in range(7)],
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert len(report.rows) == 1
    row = report.rows[0]
    assert (row.nickname, row.stored_games, row.real_games) == ("Aekk", 10, 7)


def test_a_profile_claiming_fewer_games_is_reported_as_well() -> None:
    """Drift has no preferred direction — a counter that missed a result
    leaves a profile under-reporting, which is just as wrong."""
    db = club(
        [player(P1, "Ball", games=1, wins=1)], [match(team1=[P1], team2=[P2]) for _ in range(3)]
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert (report.rows[0].stored_games, report.rows[0].real_games) == (1, 3)


def test_wins_draws_and_losses_are_judged_too_not_only_the_game_count() -> None:
    db = club(
        [player(P1, "Ball", games=3, wins=3)],
        [
            match(team1=[P1], team2=[P2], winner="team1"),
            match(team1=[P1], team2=[P2], winner="team2"),
            match(team1=[P1], team2=[P2], winner="draw"),
        ],
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    row = report.rows[0]
    assert (row.real_games, row.real_wins, row.real_draws, row.real_losses) == (3, 1, 1, 1)
    assert (row.stored_wins, row.stored_draws, row.stored_losses) == (3, 0, 0)


def test_a_match_that_is_not_finished_does_not_count_towards_anyone() -> None:
    """A queued or in-progress match has no result to count, and counting it
    would make every open night look like drift."""
    db = club(
        [player(P1, "Ball", games=1, wins=1)],
        [
            match(team1=[P1], team2=[P2]),
            match(team1=[P1], team2=[P2], status="in_progress", winner="team1"),
            match(team1=[P1], team2=[P2], status="queued", winner="team1"),
        ],
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert report.rows == []
    assert report.matches_counted == 1


def test_a_deleted_member_is_checked_as_well() -> None:
    """Their profile page still reads these counters, so it can still be
    wrong."""
    db = club([player(P1, "Gone", games=4, active=False)], [match(team1=[P1], team2=[P2])])
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert (report.rows[0].nickname, report.rows[0].is_active) == ("Gone", False)


def test_a_player_on_a_match_but_not_in_the_club_is_reported_as_an_orphan() -> None:
    """A hard-deleted member leaves their id on the matches they played.
    Those games now count for nobody, and no recount can give them back."""
    db = club([player(P1, "Ball", games=1, wins=1)], [match(team1=[P1], team2=[P4])])
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert report.orphan_player_ids == [P4]
    assert report.rows == []  # Ball's own record is still right


# --- the repair ----------------------------------------------------------


def test_a_dry_run_writes_nothing() -> None:
    db = club([player(P1, "Aekk", games=10)], [match(team1=[P1], team2=[P2])])
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert db.updates == []
    assert report.applied is False
    assert len(report.rows) == 1


def test_applying_writes_the_record_the_matches_support() -> None:
    db = club(
        [player(P1, "Aekk", games=10, wins=10)],
        [
            match(team1=[P1], team2=[P2], winner="team1"),
            match(team1=[P1], team2=[P2], winner="team2"),
        ],
    )
    stats_audit.audit(db, apply=True)  # type: ignore[arg-type]

    assert db.updates == [(P1, {"games": 2, "wins": 1, "draws": 0, "losses": 1})]


def test_applying_leaves_elo_alone() -> None:
    """A rating depends on the order its matches were played in and on the
    ratings at the time — it cannot be recomputed from these rows, so this
    must not pretend to."""
    db = club([player(P1, "Aekk", games=10)], [match(team1=[P1], team2=[P2])])
    stats_audit.audit(db, apply=True)  # type: ignore[arg-type]

    assert all("elo_score" not in payload for _, payload in db.updates)
    assert all("elo_level" not in payload for _, payload in db.updates)


def test_running_the_repair_twice_changes_nothing_the_second_time() -> None:
    db = club([player(P1, "Aekk", games=10)], [match(team1=[P1], team2=[P2])])
    stats_audit.audit(db, apply=True)  # type: ignore[arg-type]
    db.updates.clear()

    second = stats_audit.audit(db, apply=True)  # type: ignore[arg-type]

    assert (second.rows, db.updates) == ([], [])


def test_a_player_whose_record_is_already_right_is_not_written_to() -> None:
    db = club(
        [player(P1, "Ball", games=1, wins=1), player(P2, "Aekk", games=9)],
        [match(team1=[P1], team2=[P2])],
    )
    stats_audit.audit(db, apply=True)  # type: ignore[arg-type]

    assert [pid for pid, _ in db.updates] == [P2]


# --- reading the whole history, not the first page of it -----------------


def test_the_audit_reads_past_one_page_of_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """PostgREST caps a response at a page of rows. Stopping there would
    report every player above the cap as having played fewer games than they
    did — an audit that invents drift is worse than none."""
    monkeypatch.setattr(stats_audit, "PAGE", 2)
    db = club(
        [player(P1, "Ball", games=5, wins=5)],
        [match(team1=[P1], team2=[P2]) for _ in range(5)],
    )
    report = stats_audit.audit(db, apply=False)  # type: ignore[arg-type]

    assert report.matches_counted == 5
    assert report.rows == []


# --- the breakdown that settles "7 or 10?" -------------------------------


def test_a_players_games_are_split_by_the_night_they_were_played() -> None:
    db = club(
        [player(P1, "Aekk", games=10)],
        [
            *[match(team1=[P1], team2=[P2], session=NIGHT1) for _ in range(7)],
            *[match(team1=[P1], team2=[P3], session=NIGHT2) for _ in range(3)],
        ],
    )
    db.tables["sessions"] = [
        {"id": NIGHT1, "date": "2026-10-10"},
        {"id": NIGHT2, "date": "2026-09-12"},
    ]

    nights = stats_audit.spells(db, UUID(P1))  # type: ignore[arg-type]

    assert [(n.date, n.games) for n in nights] == [("2026-09-12", 3), ("2026-10-10", 7)]
    assert sum(n.games for n in nights) == 10


def test_the_breakdown_leaves_out_nights_this_player_did_not_play() -> None:
    db = club(
        [player(P1, "Aekk", games=1)],
        [match(team1=[P2], team2=[P3], session=NIGHT2), match(team1=[P1], team2=[P2])],
    )
    db.tables["sessions"] = [
        {"id": NIGHT1, "date": "2026-10-10"},
        {"id": NIGHT2, "date": "2026-09-12"},
    ]

    nights = stats_audit.spells(db, UUID(P1))  # type: ignore[arg-type]

    assert [(n.date, n.games) for n in nights] == [("2026-10-10", 1)]


def test_the_breakdown_counts_a_player_on_either_side() -> None:
    db = club(
        [player(P1, "Aekk", games=2)],
        [match(team1=[P1], team2=[P2]), match(team1=[P2], team2=[P1])],
    )
    db.tables["sessions"] = [{"id": NIGHT1, "date": "2026-10-10"}]

    assert [n.games for n in stats_audit.spells(db, UUID(P1))] == [2]  # type: ignore[arg-type]


# --- the same audit, from the admin screen --------------------------------


def api_player(pid: str, nickname: str, games: int) -> dict[str, Any]:
    """The players table as the API reads it — the audit needs every column
    the Player model does, not just the four it compares."""
    return {
        "id": pid,
        "nickname": nickname,
        "member_seq": 1,
        "avatar_url": None,
        "elo_score": 1200,
        "elo_level": "highball",
        "is_active": True,
        "line_id": None,
        "dominant_hand": None,
        "tiktok": None,
        "instagram": None,
        "quote": None,
        "created_at": "2026-10-01T10:00:00+00:00",
        "games": games,
        "wins": 0,
        "draws": 0,
        "losses": 0,
    }


def admin_auth() -> dict[str, str]:
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def test_the_screen_can_ask_who_disagrees_with_their_matches(
    client: Any, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [api_player(P1, "Aekk", 10)]
    supabase_rows["matches"] = [match(team1=[P1], team2=[P2]) for _ in range(7)]

    response = client.get("/api/admin/stats-audit", headers=admin_auth())

    assert response.status_code == 200
    body = response.json()
    assert body["applied"] is False
    assert [(r["nickname"], r["stored_games"], r["real_games"]) for r in body["rows"]] == [
        ("Aekk", 10, 7)
    ]


def test_asking_writes_nothing(
    client: Any, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [api_player(P1, "Aekk", 10)]
    supabase_rows["matches"] = [match(team1=[P1], team2=[P2])]

    client.get("/api/admin/stats-audit", headers=admin_auth())

    assert [c for c in supabase_spy.calls if c[0] == "update"] == []


def test_the_repair_writes_the_record_the_matches_support(
    client: Any, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [api_player(P1, "Aekk", 10)]
    supabase_rows["matches"] = [match(team1=[P1], team2=[P2]) for _ in range(7)]

    response = client.post("/api/admin/stats-audit/repair", headers=admin_auth())

    assert response.status_code == 200
    assert response.json()["applied"] is True
    written = [c[1][0] for c in supabase_spy.calls if c[0] == "update"]
    assert written == [{"games": 7, "wins": 7, "draws": 0, "losses": 0}]


def test_the_repair_never_writes_elo(
    client: Any, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [api_player(P1, "Aekk", 10)]
    supabase_rows["matches"] = [match(team1=[P1], team2=[P2])]

    client.post("/api/admin/stats-audit/repair", headers=admin_auth())

    for payload in (c[1][0] for c in supabase_spy.calls if c[0] == "update"):
        assert "elo_score" not in payload and "elo_level" not in payload


def test_neither_is_open_to_anyone_without_a_login(
    client: Any, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """These read every player's record and one of them rewrites it."""
    supabase_rows["players"] = []
    assert client.get("/api/admin/stats-audit").status_code == 401
    assert client.post("/api/admin/stats-audit/repair").status_code == 401
