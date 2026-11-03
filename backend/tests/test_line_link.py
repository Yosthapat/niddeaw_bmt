"""Linking a LINE account to a member: the member picks, an admin approves.

Runs against the uxlab's in-memory database (tools/uxlab/minisupabase.py),
which applies filters, because the whole point here is which rows a query
finds: whose link is pending, who is already taken."""

import os
import sys
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.config import get_settings
from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token
from app.services import line_auth

BALL = "U" + "a" * 32
BANK = "U" + "b" * 32


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def member(user_id: str = BALL, name: str = "บอล Ballz") -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(user_id, name)}"}


def player(nickname: str, seq: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "nickname": nickname,
        "member_seq": seq,
        "elo_score": 1000,
        "elo_level": "beer",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        **extra,
    }


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[MiniSupabase]:
    settings = get_settings()
    monkeypatch.setattr(settings, "line_login_channel_id", "1234567890")
    monkeypatch.setattr(settings, "line_liff_id", "1234567890-AbCdEfGh")
    fake = MiniSupabase(
        {
            "players": [
                player("Ball", 1),
                player("Bank", 2),
                player("Bam", 3, line_user_id="U" + "c" * 32),
            ],
            "admins": [],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


def pid(db: MiniSupabase, nickname: str) -> str:
    return next(str(p["id"]) for p in db.tables["players"] if p["nickname"] == nickname)


def test_config_says_off_until_both_ids_are_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "line_liff_id", None)
    assert client.get("/api/line/config").json() == {"enabled": False, "liff_id": None}
    assert client.post("/api/line/session", json={"id_token": "x" * 40}).status_code == 503


def test_a_session_comes_only_from_a_token_line_vouched_for(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    def verify(token: str) -> line_auth.LineProfile:
        if token != "good-token-from-line-xxxxx":
            raise line_auth.LineAuthError("refused")
        return line_auth.LineProfile(
            user_id=BALL, name="บอล Ballz", picture="https://profile.line-scdn.net/x"
        )

    monkeypatch.setattr(line_auth, "verify_id_token", verify)
    assert (
        client.post("/api/line/session", json={"id_token": "forged-token-xxxxxxxxxx"}).status_code
        == 401
    )
    body = client.post("/api/line/session", json={"id_token": "good-token-from-line-xxxxx"}).json()
    assert body["line_name"] == "บอล Ballz" and body["player"] is None and body["token"]
    me = client.get("/api/line/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200 and me.json()["line_picture"] == "https://profile.line-scdn.net/x"


def test_a_members_token_opens_no_admin_route_and_an_admins_no_member_route(
    client: TestClient, db: MiniSupabase
) -> None:
    assert client.get("/api/admin/line/requests", headers=member()).status_code == 401
    assert client.get("/api/admin/sessions", headers=member()).status_code == 401
    assert client.get("/api/line/me", headers=admin()).status_code == 401


def test_pick_approve_and_the_link_is_made(client: TestClient, db: MiniSupabase) -> None:
    options = client.get("/api/line/link/options", headers=member()).json()
    assert {o["nickname"]: o["taken"] for o in options} == {
        "Bam": True,
        "Ball": False,
        "Bank": False,
    }

    picked = client.post(
        "/api/line/link", json={"player_id": pid(db, "Bank")}, headers=member()
    ).json()
    assert picked["pending"]["player"]["nickname"] == "Bank"
    # Wrong name: picking again replaces the request, not adds one.
    picked = client.post(
        "/api/line/link", json={"player_id": pid(db, "Ball")}, headers=member()
    ).json()
    assert picked["pending"]["player"]["nickname"] == "Ball"
    requests = client.get("/api/admin/line/requests", headers=admin()).json()
    assert [r["player"]["nickname"] for r in requests] == ["Ball"]

    linked = client.post(f"/api/admin/line/requests/{requests[0]['id']}/approve", headers=admin())
    assert linked.status_code == 200
    status = client.get("/api/line/me", headers=member()).json()
    assert status["player"]["nickname"] == "Ball" and status["pending"] is None
    assert client.get("/api/admin/line/requests", headers=admin()).json() == []
    # Linked now: picking someone else is refused.
    again = client.post("/api/line/link", json={"player_id": pid(db, "Bank")}, headers=member())
    assert again.status_code == 409
    assert {"player_id": pid(db, "Ball"), "line_name": "บอล Ballz"} in client.get(
        "/api/admin/line/links", headers=admin()
    ).json()


def test_a_name_already_linked_cannot_be_picked(client: TestClient, db: MiniSupabase) -> None:
    taken = client.post("/api/line/link", json={"player_id": pid(db, "Bam")}, headers=member())
    assert taken.status_code == 409
    assert "Bam" in taken.json()["detail"]


def test_approving_one_claim_refuses_the_others_for_the_same_name(
    client: TestClient, db: MiniSupabase
) -> None:
    client.post("/api/line/link", json={"player_id": pid(db, "Ball")}, headers=member(BALL))
    client.post("/api/line/link", json={"player_id": pid(db, "Ball")}, headers=member(BANK, "แบงก์"))
    first = next(
        r
        for r in client.get("/api/admin/line/requests", headers=admin()).json()
        if r["line_name"] == "บอล Ballz"
    )
    client.post(f"/api/admin/line/requests/{first['id']}/approve", headers=admin())
    assert client.get("/api/admin/line/requests", headers=admin()).json() == []
    assert client.get("/api/line/me", headers=member(BANK, "แบงก์")).json()["pending"] is None


def test_refuse_cancel_and_unlink(client: TestClient, db: MiniSupabase) -> None:
    client.post("/api/line/link", json={"player_id": pid(db, "Ball")}, headers=member())
    assert client.delete("/api/line/link", headers=member()).json()["pending"] is None

    client.post("/api/line/link", json={"player_id": pid(db, "Ball")}, headers=member())
    req = client.get("/api/admin/line/requests", headers=admin()).json()[0]
    assert (
        client.post(f"/api/admin/line/requests/{req['id']}/reject", headers=admin()).status_code
        == 204
    )
    assert (
        client.post(f"/api/admin/line/requests/{req['id']}/approve", headers=admin()).status_code
        == 404
    )
    assert client.get("/api/line/me", headers=member()).json()["pending"] is None

    bam = pid(db, "Bam")
    assert client.post(f"/api/admin/line/players/{bam}/unlink", headers=admin()).status_code == 200
    assert not next(
        o
        for o in client.get("/api/line/link/options", headers=member()).json()
        if o["nickname"] == "Bam"
    )["taken"]


def test_verify_id_token_asks_line_for_our_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "line_login_channel_id", "1234567890")
    sent: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["form"] = dict(httpx.QueryParams(request.content.decode()))
        if sent["form"]["id_token"] == "bad":
            return httpx.Response(400, json={"error": "invalid_request"})
        return httpx.Response(
            200, json={"sub": BALL, "name": "บอล", "picture": "https://p.example/x.jpg"}
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    profile = line_auth.verify_id_token("good", http)
    assert sent["form"] == {"id_token": "good", "client_id": "1234567890"}
    assert profile == line_auth.LineProfile(
        user_id=BALL, name="บอล", picture="https://p.example/x.jpg"
    )
    with pytest.raises(line_auth.LineAuthError):
        line_auth.verify_id_token("bad", http)
