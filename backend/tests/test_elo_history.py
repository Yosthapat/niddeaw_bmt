"""Working each finished match's pre-match ELO back from today's ratings."""

import os
import sys
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.services import elo_history, elo_service

SESSION = str(uuid4())


def _player(nick: str, elo: int) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "nickname": nick,
        "elo_score": elo,
        "elo_level": elo_service.get_tier(elo),
        "member_seq": 1,
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
    }


def _play(
    db: MiniSupabase, n: int, t1: list[dict[str, Any]], t2: list[dict[str, Any]], winner: str
) -> tuple[float, float, str]:
    """Record a result the way the app does: deltas from the ratings now,
    applied to the players, stored on the match. Returns the ratings going
    in and the match id."""
    before = (
        elo_service.team_rating([p["elo_score"] for p in t1]),
        elo_service.team_rating([p["elo_score"] for p in t2]),
    )
    d1, d2 = elo_service.compute_deltas(
        [p["elo_score"] for p in t1], [p["elo_score"] for p in t2], winner
    )
    for p in t1:
        p["elo_score"] += d1
    for p in t2:
        p["elo_score"] += d2
    mid = str(uuid4())
    db.tables["matches"].append(
        {
            "id": mid,
            "session_id": SESSION,
            "type": "double",
            "match_no": n,
            "team1_player_ids": [p["id"] for p in t1],
            "team2_player_ids": [p["id"] for p in t2],
            "winner": winner,
            "status": "completed",
            "court": "1",
            "sets": None,
            "elo_delta_team1": d1,
            "elo_delta_team2": d2,
            "created_at": f"2026-11-0{n}T19:00:00Z",
            "updated_at": f"2026-11-0{n}T19:30:00Z",
        }
    )
    return before[0], before[1], mid


@pytest.fixture
def club() -> Iterator[tuple[MiniSupabase, list[dict[str, Any]]]]:
    ps = [_player("Ball", 1300), _player("James", 1100), _player("Faa", 1500), _player("Ton", 900)]
    db = MiniSupabase({"players": ps, "matches": [], "sessions": []})
    db.tables["matches_numbered"] = db.tables["matches"]
    app.dependency_overrides[get_supabase] = lambda: db
    yield db, ps
    app.dependency_overrides.pop(get_supabase, None)


def test_ratings_going_into_each_match_are_worked_back(
    club: tuple[MiniSupabase, list[dict[str, Any]]],
) -> None:
    db, (ball, james, faa, ton) = club
    a = _play(db, 1, [ball, james], [faa, ton], "team2")
    b = _play(db, 2, [ball, faa], [james, ton], "team1")
    c = _play(db, 3, [ball, ton], [james, faa], "team1")  # an upset: 1100 vs 1300
    got = elo_history.before_ratings(db)
    for before1, before2, mid in (a, b, c):
        assert got[mid] == pytest.approx((before1, before2))


def test_a_match_without_a_recorded_change_is_left_out(
    club: tuple[MiniSupabase, list[dict[str, Any]]],
) -> None:
    db, (ball, james, faa, ton) = club
    _, _, mid = _play(db, 1, [ball, james], [faa, ton], "team1")
    db.tables["matches"][0]["elo_delta_team1"] = None
    assert mid not in elo_history.before_ratings(db)


def test_match_list_and_detail_carry_the_ratings(
    client: TestClient, club: tuple[MiniSupabase, list[dict[str, Any]]]
) -> None:
    db, (ball, james, faa, ton) = club
    b1, b2, _ = _play(db, 1, [ball, james], [faa, ton], "team2")
    listed = client.get("/api/matches").json()
    assert listed[0]["elo_team1"] == pytest.approx(b1, abs=0.1) and listed[0][
        "elo_team2"
    ] == pytest.approx(b2, abs=0.1)
    mine = client.get(f"/api/players/{ball['id']}/matches").json()
    assert mine[0]["elo_team1"] == pytest.approx(b1, abs=0.1)


def test_a_match_not_played_yet_uses_ratings_now(
    club: tuple[MiniSupabase, list[dict[str, Any]]],
) -> None:
    db, (ball, james, faa, ton) = club
    got = elo_history.current_ratings(db, [ball["id"], james["id"]], [faa["id"], ton["id"]])
    assert got == (1200, 1200)
    assert elo_history.current_ratings(db, [ball["id"]], [uuid4()]) is None
