"""The Friday check-in reminder: who gets it, that it goes out once per
night, and that it never spends more of the OA's LINE quota than is left."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import get_supabase
from app.main import app
from app.services import line_reminder
from tests.conftest import FakeSupabase

TODAY = date(2026, 11, 6)


def uid(n: int) -> str:
    return "U" + f"{n:032x}"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("LINE_MESSAGING_TOKEN", "tok")
    monkeypatch.setenv("LINE_REMINDER_SECRET", "s3cret")
    monkeypatch.setenv("LINE_LIFF_ID", "123-abc")
    monkeypatch.setattr(line_reminder, "_today", lambda: TODAY)
    yield
    get_settings.cache_clear()


def club(*, sent_at: str | None = None) -> tuple[FakeSupabase, dict[str, str]]:
    """Tonight open; four earlier nights. Players: A and B came last week,
    C came a month and a half ago (too long), D is here already, E came but
    never linked LINE, F linked but is inactive."""
    nights = {"tonight": str(uuid4())} | {f"w{k}": str(uuid4()) for k in range(1, 7)}
    sessions = [{"id": nights["tonight"], "date": TODAY.isoformat(), "status": "open",
                 "line_reminder_sent_at": sent_at}]
    sessions += [{"id": nights[f"w{k}"], "date": (TODAY - timedelta(days=7 * k)).isoformat(), "status": "closed"}
                 for k in range(1, 7)]
    p = {x: str(uuid4()) for x in "ABCDEF"}
    players = [
        {"id": p["A"], "line_user_id": uid(1), "is_active": True},
        {"id": p["B"], "line_user_id": uid(2), "is_active": True},
        {"id": p["C"], "line_user_id": uid(3), "is_active": True},
        {"id": p["D"], "line_user_id": uid(4), "is_active": True},
        {"id": p["E"], "line_user_id": None, "is_active": True},
        {"id": p["F"], "line_user_id": uid(6), "is_active": False},
    ]
    checkins = [
        {"session_id": nights["w1"], "player_id": p["B"]},
        {"session_id": nights["w3"], "player_id": p["A"]},
        {"session_id": nights["w6"], "player_id": p["C"]},  # older than the last 4 nights
        {"session_id": nights["w1"], "player_id": p["D"]},
        {"session_id": nights["tonight"], "player_id": p["D"]},
        {"session_id": nights["w2"], "player_id": p["E"]},
        {"session_id": nights["w2"], "player_id": p["F"]},
    ]
    return FakeSupabase({"sessions": sessions, "players": players, "checkins": checkins}), nights


def line_api(quota: dict[str, Any], used: int = 0) -> tuple[httpx.Client, list[dict[str, Any]]]:
    pushed: list[dict[str, Any]] = []

    def handle(req: httpx.Request) -> httpx.Response:
        assert req.headers["Authorization"] == "Bearer tok"
        if req.url.path.endswith("/message/quota"):
            return httpx.Response(200, json=quota)
        if req.url.path.endswith("/quota/consumption"):
            return httpx.Response(200, json={"totalUsage": used})
        if req.url.path.endswith("/message/multicast"):
            pushed.append(json.loads(req.content))
            return httpx.Response(200, json={})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handle)), pushed


def test_reminds_recent_linked_members_not_yet_here() -> None:
    db, _ = club()
    http, pushed = line_api({"type": "limited", "value": 300})
    done = line_reminder.send(db, http)
    assert (done.sent, done.reason) == (2, "sent")
    # B (last week) before A (three weeks ago); C too long ago, D here,
    # E not linked, F inactive.
    assert pushed[0]["to"] == [uid(2), uid(1)]
    text = pushed[0]["messages"][0]["text"]
    assert "เช็คอิน" in text and "https://liff.line.me/123-abc/checkin" in text


def test_never_more_than_the_quota_left() -> None:
    db, _ = club()
    http, pushed = line_api({"type": "limited", "value": 300}, used=299)
    assert line_reminder.send(db, http).sent == 1
    assert pushed[0]["to"] == [uid(2)]  # the most recent player keeps the last message


def test_quota_used_up_sends_nothing_and_leaves_the_night_unclaimed() -> None:
    db, _ = club()
    http, pushed = line_api({"type": "limited", "value": 300}, used=300)
    done = line_reminder.send(db, http)
    assert (done.sent, pushed) == (0, [])
    assert "quota" in done.reason
    assert ("update", ({"line_reminder_sent_at": None, "line_reminder_count": None},), {}) in db.calls


def test_once_per_night() -> None:
    db, _ = club(sent_at="2026-11-06T12:31:00+00:00")
    http, pushed = line_api({"type": "none"})
    assert line_reminder.send(db, http).reason == "already sent tonight"
    assert pushed == []


def test_no_open_night_no_reminder() -> None:
    db, _ = club()
    db.tables["sessions"][0]["status"] = "closed"
    http, pushed = line_api({"type": "none"})
    assert line_reminder.send(db, http).reason == "no open night today"
    assert pushed == []


def test_without_a_token_nothing_happens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINE_MESSAGING_TOKEN")
    get_settings.cache_clear()
    db, _ = club()
    assert line_reminder.send(db).reason.startswith("not set up")


def test_line_refusing_releases_the_night() -> None:
    db, _ = club()

    def handle(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/message/quota"):
            return httpx.Response(200, json={"type": "none"})
        return httpx.Response(401, json={"message": "Authentication failed"})

    with pytest.raises(httpx.HTTPStatusError):
        line_reminder.send(db, httpx.Client(transport=httpx.MockTransport(handle)))
    assert ("update", ({"line_reminder_sent_at": None, "line_reminder_count": None},), {}) in db.calls


@pytest.fixture
def client() -> Iterator[TestClient]:
    db, _ = club(sent_at="2026-11-06T12:31:00+00:00")
    app.dependency_overrides[get_supabase] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.pop(get_supabase, None)


def test_endpoint_needs_the_secret(client: TestClient) -> None:
    url = "/api/internal/line-checkin-reminder"
    assert client.post(url).status_code == 403
    assert client.post(url, headers={"X-Reminder-Secret": "wrong"}).status_code == 403
    res = client.post(url, headers={"X-Reminder-Secret": "s3cret"})
    assert res.status_code == 200
    assert res.json() == {"sent": 0, "reason": "already sent tonight"}


def test_endpoint_is_off_without_a_secret(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINE_REMINDER_SECRET")
    get_settings.cache_clear()
    assert client.post("/api/internal/line-checkin-reminder", headers={"X-Reminder-Secret": "x"}).status_code == 404
