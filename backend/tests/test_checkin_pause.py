"""Resting a member between games: still in for the night, out of pairings."""

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
NAMES = ["Ball", "Bank", "Faa", "Ton", "Oum"]


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    players = [
        {
            "id": str(uuid4()),
            "nickname": n,
            "member_seq": i + 1,
            "elo_score": 1000,
            "elo_level": "beer",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
        }
        for i, n in enumerate(NAMES)
    ]
    fake = MiniSupabase(
        {
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "players": players,
            "sessions": [
                {
                    "id": SESSION_ID,
                    "date": "2026-11-15",
                    "location": "KB",
                    "status": "open",
                    "court_fee_per_person": 80,
                    "shuttlecock_price_per_game": 29,
                    "created_at": "2026-11-15T18:00:00Z",
                }
            ],
            "checkins": [
                {
                    "id": str(uuid4()),
                    "session_id": SESSION_ID,
                    "player_id": p["id"],
                    "checkin_time": "2026-11-15T18:05:00Z",
                    "checkout_time": None,
                }
                for p in players
            ],
            "matches": [],
            "pairing_history": [],
            "locked_pairs": [],
            "admin_activity_log": [],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, name: str) -> str:
    return str(next(p["id"] for p in db.tables["players"] if p["nickname"] == name))


def queue(client: TestClient) -> dict[str, Any]:
    res = client.get(f"/api/admin/matchmaking/queue?session_id={SESSION_ID}", headers=admin())
    assert res.status_code == 200, res.text
    return res.json()


def in_play(q: dict[str, Any]) -> set[str]:
    """Everyone the queue would pair: in a suggestion or waiting for one."""
    ids = {w["player_id"] for w in q["waiting"]}
    for s in q["suggestions"]:
        ids |= set(s["team1_player_ids"]) | set(s["team2_player_ids"])
    return ids


def test_a_resting_member_is_left_out_of_pairings_until_brought_back(
    client: TestClient, db: MiniSupabase
) -> None:
    faa = pid(db, "Faa")
    body = {"session_id": SESSION_ID, "player_id": faa}

    res = client.post("/api/admin/checkins/pause", json=body, headers=admin())
    assert res.status_code == 200, res.text
    assert res.json()["paused_at"] and res.json()["checkout_time"] is None

    q = queue(client)
    assert faa not in in_play(q)
    assert [p["player_id"] for p in q["paused"]] == [faa]
    assert len(q["suggestions"]) == 1  # the other four still play

    res = client.post("/api/admin/checkins/resume", json=body, headers=admin())
    assert res.status_code == 200 and res.json()["paused_at"] is None
    q = queue(client)
    assert faa in in_play(q) and q["paused"] == []


def test_checking_back_in_after_going_home_is_not_still_resting(
    client: TestClient, db: MiniSupabase
) -> None:
    ton = pid(db, "Ton")
    client.post(
        "/api/admin/checkins/pause",
        json={"session_id": SESSION_ID, "player_id": ton},
        headers=admin(),
    )
    row = next(c for c in db.tables["checkins"] if c["player_id"] == ton)
    assert (
        client.post(f"/api/admin/checkins/{row['id']}/checkout", headers=admin()).status_code == 200
    )
    # gone home: neither resting nor waiting
    assert ton not in in_play(queue(client)) and queue(client)["paused"] == []

    back = client.post(
        "/api/admin/checkins", json={"session_id": SESSION_ID, "player_id": ton}, headers=admin()
    )
    assert back.status_code == 201, back.text
    assert back.json()["paused_at"] is None
    assert ton in in_play(queue(client))


def test_only_someone_checked_in_can_rest_and_only_an_admin_can_say_so(
    client: TestClient, db: MiniSupabase
) -> None:
    stranger = {"session_id": SESSION_ID, "player_id": str(uuid4())}
    assert (
        client.post("/api/admin/checkins/pause", json=stranger, headers=admin()).status_code == 404
    )
    body = {"session_id": SESSION_ID, "player_id": pid(db, "Ball")}
    assert client.post("/api/admin/checkins/pause", json=body).status_code == 401
    assert client.post("/api/admin/checkins/resume", json=body).status_code == 401
