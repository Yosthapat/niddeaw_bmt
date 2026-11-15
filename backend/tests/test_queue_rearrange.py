"""Fixing a queued pairing without cancelling it: moving a queued match up or
down the queue, and swapping two players (across the net, between queued
matches, or with someone waiting)."""

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
from app.security import create_access_token

ADMIN_ID = str(uuid4())
SESSION_ID = str(uuid4())
NAMES = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    players = [
        {"id": str(uuid4()), "nickname": n, "member_seq": i + 1, "elo_score": 1000, "elo_level": "beer",
         "is_active": True, "created_at": "2026-01-01T00:00:00Z"}
        for i, n in enumerate(NAMES)
    ]  # fmt: skip
    fake = MiniSupabase(
        {
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "players": players,
            "sessions": [{"id": SESSION_ID, "date": "2026-11-15", "location": "KB", "status": "open",
                          "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
                          "created_at": "2026-11-15T18:00:00Z"}],
            "checkins": [{"id": str(uuid4()), "session_id": SESSION_ID, "player_id": p["id"],
                          "checkin_time": "2026-11-15T18:05:00Z", "checkout_time": None} for p in players],
            "matches": [],
            "pairing_history": [],
            "locked_pairs": [],
            "admin_activity_log": [],
        }
    )  # fmt: skip
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, name: str) -> str:
    return str(next(p["id"] for p in db.tables["players"] if p["nickname"] == name))


def name(db: MiniSupabase, player_id: str) -> str:
    return str(next(p["nickname"] for p in db.tables["players"] if p["id"] == player_id))


def queue(client: TestClient, db: MiniSupabase, n: str, *teams: str) -> str:
    """Confirm a queued match: queue(client, db, "AB", "CD")."""
    t1, t2 = teams[0], teams[1]
    res = client.post(
        "/api/admin/matchmaking/confirm",
        json={
            "session_id": SESSION_ID,
            "type": "double",
            "team1_player_ids": [pid(db, x) for x in t1],
            "team2_player_ids": [pid(db, x) for x in t2],
            "status": "queued",
        },
        headers=admin(),
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def lineup(client: TestClient, db: MiniSupabase) -> list[str]:
    """The queued matches in queue order, as "AB-CD"."""
    q = client.get(f"/api/admin/matchmaking/queue?session_id={SESSION_ID}", headers=admin()).json()
    return [
        "".join(name(db, p) for p in m["team1_player_ids"])
        + "-"
        + "".join(name(db, p) for p in m["team2_player_ids"])
        for m in q["queued"]
    ]


def teammates(db: MiniSupabase, match_id: str) -> set[frozenset[str]]:
    return {
        frozenset({name(db, h["player_a_id"]), name(db, h["player_b_id"])})
        for h in db.tables["pairing_history"]
        if h["match_id"] == match_id and h["relation"] == "teammate"
    }


def swap(client: TestClient, db: MiniSupabase, a: str, b: str) -> Any:
    return client.post(
        "/api/admin/matchmaking/swap",
        json={"session_id": SESSION_ID, "player_a_id": pid(db, a), "player_b_id": pid(db, b)},
        headers=admin(),
    )


def test_a_queued_match_moves_up_and_down_and_its_number_with_it(
    client: TestClient, db: MiniSupabase
) -> None:
    first = queue(client, db, "1", "AB", "CD")
    second = queue(client, db, "2", "EF", "GH")
    assert lineup(client, db) == ["AB-CD", "EF-GH"]

    res = client.post(
        f"/api/admin/matchmaking/matches/{second}/move", json={"direction": "up"}, headers=admin()
    )
    assert res.status_code == 200, res.text
    queued = res.json()["queued"]
    assert [m["match_id"] for m in queued] == [second, first]
    assert queued[0]["match_no"] < queued[1]["match_no"]

    # already at the top: nothing moves
    client.post(
        f"/api/admin/matchmaking/matches/{second}/move", json={"direction": "up"}, headers=admin()
    )
    assert lineup(client, db) == ["EF-GH", "AB-CD"]
    client.post(
        f"/api/admin/matchmaking/matches/{second}/move", json={"direction": "down"}, headers=admin()
    )
    assert lineup(client, db) == ["AB-CD", "EF-GH"]


def test_only_a_queued_match_moves(client: TestClient, db: MiniSupabase) -> None:
    match_id = queue(client, db, "1", "AB", "CD")
    assert (
        client.post(f"/api/admin/matchmaking/matches/{match_id}/start", headers=admin()).status_code
        == 200
    )
    res = client.post(
        f"/api/admin/matchmaking/matches/{match_id}/move", json={"direction": "up"}, headers=admin()
    )
    assert res.status_code == 409


def test_swapping_between_two_queued_matches_keeps_both_and_their_history(
    client: TestClient, db: MiniSupabase
) -> None:
    first = queue(client, db, "1", "AB", "CD")
    second = queue(client, db, "2", "EF", "GH")
    assert swap(client, db, "B", "E").status_code == 200
    assert lineup(client, db) == ["AE-CD", "BF-GH"]
    assert teammates(db, first) == {frozenset("AE"), frozenset("CD")}
    assert teammates(db, second) == {frozenset("BF"), frozenset("GH")}
    # the same swap again puts it back
    swap(client, db, "B", "E")
    assert lineup(client, db) == ["AB-CD", "EF-GH"]


def test_swapping_across_the_net(client: TestClient, db: MiniSupabase) -> None:
    queue(client, db, "1", "AB", "CD")
    swap(client, db, "A", "C")
    assert lineup(client, db) == ["CB-AD"]


def test_someone_waiting_takes_a_queued_players_place(client: TestClient, db: MiniSupabase) -> None:
    queue(client, db, "1", "AB", "CD")
    assert swap(client, db, "A", "I").status_code == 200
    assert lineup(client, db) == ["IB-CD"]
    q = client.get(f"/api/admin/matchmaking/queue?session_id={SESSION_ID}", headers=admin()).json()
    free = {p for s in q["suggestions"] for p in s["team1_player_ids"] + s["team2_player_ids"]}
    free |= {w["player_id"] for w in q["waiting"]}
    assert pid(db, "A") in free and pid(db, "I") not in free


def test_who_cannot_be_swapped_in(client: TestClient, db: MiniSupabase) -> None:
    queue(client, db, "1", "AB", "CD")
    # resting
    next(c for c in db.tables["checkins"] if c["player_id"] == pid(db, "I"))["paused_at"] = (
        "2026-11-15T19:00:00Z"
    )
    assert swap(client, db, "A", "I").status_code == 409
    # gone home
    next(c for c in db.tables["checkins"] if c["player_id"] == pid(db, "H"))["checkout_time"] = (
        "2026-11-15T19:00:00Z"
    )
    assert swap(client, db, "A", "H").status_code == 409
    # neither is in a queued match
    assert swap(client, db, "E", "F").status_code == 409
    assert lineup(client, db) == ["AB-CD"]


def test_rearranging_is_for_admins(client: TestClient, db: MiniSupabase) -> None:
    match_id = queue(client, db, "1", "AB", "CD")
    assert (
        client.post(
            f"/api/admin/matchmaking/matches/{match_id}/move", json={"direction": "up"}
        ).status_code
        == 401
    )
    body = {"session_id": SESSION_ID, "player_a_id": pid(db, "A"), "player_b_id": pid(db, "I")}
    assert client.post("/api/admin/matchmaking/swap", json=body).status_code == 401
