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


# --- signing up through LINE -------------------------------------------------

from app.services import line_join


def _png() -> bytes:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (40, 40), (234, 76, 164)).save(out, "PNG")
    return out.getvalue()


def joiner(user_id: str = "U" + "d" * 32, name: str = "Tonkla LINE") -> dict[str, str]:
    token = create_line_token(user_id, name, "https://profile.line-scdn.net/0hTonkla")
    return {"Authorization": f"Bearer {token}"}


def joins(db: MiniSupabase) -> list[dict[str, Any]]:
    return db.tables.get("line_join_requests", [])


def test_sign_up_keeps_the_club_rules_and_uses_the_line_picture(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetched: list[str] = []
    monkeypatch.setattr(line_join, "fetch_line_picture", lambda url: fetched.append(url) or _png())
    form = {"nickname": "Tonkla", "dominant_hand": "right", "instagram": "tonkla.bmt"}

    assert (
        client.post(
            "/api/line/join", json={**form, "nickname": "ต้นกล้า"}, headers=joiner()
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/line/join", json={**form, "nickname": "BALL"}, headers=joiner()
        ).status_code
        == 409
    )

    sent = client.post("/api/line/join", json=form, headers=joiner()).json()
    assert sent["application"]["nickname"] == "Tonkla"
    assert sent["application"]["photo_url"].startswith(db.public_base)
    assert fetched == ["https://profile.line-scdn.net/0hTonkla"]
    # Someone else can't queue up behind them with the same name.
    other = client.post("/api/line/join", json=form, headers=joiner("U" + "e" * 32, "x"))
    assert other.status_code == 409
    # Sending again replaces, not adds.
    again = client.post(
        "/api/line/join", json={**form, "quote": "ตบไม่ลง ไม่กลับบ้าน"}, headers=joiner()
    )
    assert again.json()["application"]["quote"] == "ตบไม่ลง ไม่กลับบ้าน"
    assert len([j for j in joins(db) if j["status"] == "pending"]) == 1
    # Nobody is in the club yet.
    assert not any(p["nickname"] == "Tonkla" for p in db.tables["players"])

    # However they type it, it is saved a capital then small letters.
    tidied = client.post("/api/line/join", json={**form, "nickname": "tONKLA"}, headers=joiner())
    assert tidied.json()["application"]["nickname"] == "Tonkla"


def test_admin_accepts_a_sign_up_into_a_linked_member(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(line_join, "fetch_line_picture", lambda url: None)
    client.post(
        "/api/line/join", json={"nickname": "Tonkla", "use_line_photo": False}, headers=joiner()
    )
    photo = client.post(
        "/api/line/join/photo", files={"file": ("me.png", _png(), "image/png")}, headers=joiner()
    )
    assert photo.json()["application"]["photo_url"]
    bad = client.post(
        "/api/line/join/photo", files={"file": ("x.png", b"nope", "image/png")}, headers=joiner()
    )
    assert bad.status_code == 400

    waiting = client.get("/api/admin/line/joins", headers=admin()).json()
    assert [(j["nickname"], j["line_name"]) for j in waiting] == [("Tonkla", "Tonkla LINE")]
    made = client.post(
        f"/api/admin/line/joins/{waiting[0]['id']}/approve",
        json={"elo_score": 800},
        headers=admin(),
    )
    assert made.status_code == 200
    assert made.json()["elo_level"] == "milk"
    assert made.json()["avatar_url"] == photo.json()["application"]["photo_url"]
    row = next(p for p in db.tables["players"] if p["nickname"] == "Tonkla")
    assert row["line_user_id"] == "U" + "d" * 32

    me = client.get("/api/line/me", headers=joiner()).json()
    assert me["player"]["nickname"] == "Tonkla" and me["application"] is None
    assert (
        client.post(
            f"/api/admin/line/joins/{waiting[0]['id']}/approve", json={}, headers=admin()
        ).status_code
        == 404
    )
    # A member already can't sign up again.
    assert (
        client.post("/api/line/join", json={"nickname": "Tonkla Two"}, headers=joiner()).status_code
        == 409
    )


def test_the_name_is_checked_again_when_the_admin_accepts(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(line_join, "fetch_line_picture", lambda url: None)
    client.post("/api/line/join", json={"nickname": "Tonkla"}, headers=joiner())
    db.tables["players"].append(player("Tonkla", 9))  # added by an admin meanwhile
    req = client.get("/api/admin/line/joins", headers=admin()).json()[0]
    assert (
        client.post(
            f"/api/admin/line/joins/{req['id']}/approve", json={}, headers=admin()
        ).status_code
        == 409
    )


def test_reject_withdraw_and_switching_between_claim_and_sign_up(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(line_join, "fetch_line_picture", lambda url: _png())
    client.post("/api/line/join", json={"nickname": "Tonkla"}, headers=joiner())
    req = client.get("/api/admin/line/joins", headers=admin()).json()[0]
    assert (
        client.post(f"/api/admin/line/joins/{req['id']}/reject", headers=admin()).status_code == 204
    )
    assert client.get("/api/line/me", headers=joiner()).json()["application"] is None
    assert db.storage_files == {}  # their photo went with it

    # Signing up drops a name claim, and claiming a name drops a sign-up.
    client.post("/api/line/link", json={"player_id": pid(db, "Bank")}, headers=joiner())
    after = client.post("/api/line/join", json={"nickname": "Tonkla"}, headers=joiner()).json()
    assert after["pending"] is None and after["application"]["nickname"] == "Tonkla"
    after = client.post(
        "/api/line/link", json={"player_id": pid(db, "Bank")}, headers=joiner()
    ).json()
    assert after["application"] is None and after["pending"]["player"]["nickname"] == "Bank"
    client.post("/api/line/join", json={"nickname": "Tonkla"}, headers=joiner())
    assert client.delete("/api/line/join", headers=joiner()).json()["application"] is None


def test_only_line_pictures_are_fetched() -> None:
    assert line_join.is_line_picture("https://profile.line-scdn.net/0habc")
    assert not line_join.is_line_picture("http://profile.line-scdn.net/0habc")
    assert not line_join.is_line_picture("https://evil.example/line-scdn.net")
    assert not line_join.is_line_picture("https://line-scdn.net.evil.example/x")
    assert line_join.fetch_line_picture("https://169.254.169.254/latest") is None


# --- checking in by scanning tonight's QR ------------------------------------

from datetime import timedelta

from app.services import line_checkin

BAM = "U" + "c" * 32  # Bam is linked in the fixture


def night(db: MiniSupabase, *, days_ago: int = 0, status: str = "open") -> str:
    sid = str(uuid4())
    day = line_checkin._today() - timedelta(days=days_ago)
    db.tables.setdefault("sessions", []).append(
        {
            "id": sid,
            "date": day.isoformat(),
            "location": "KB court",
            "court_fee_per_person": 80,
            "shuttlecock_price_per_game": 29,
            "status": status,
            "created_by": str(uuid4()),
            "created_at": "2026-01-01T00:00:00Z",
            "line_checkin_code": None,
        }
    )
    return sid


def test_admin_qr_is_kept_for_the_night_until_replaced(
    client: TestClient, db: MiniSupabase
) -> None:
    sid = night(db)
    first = client.get(f"/api/admin/line/checkin-qr?session_id={sid}", headers=admin()).json()
    assert first["url"] == f"https://liff.line.me/1234567890-AbCdEfGh/checkin?c={first['code']}"
    assert first["qr"].startswith("data:image/png;base64,")
    again = client.get(f"/api/admin/line/checkin-qr?session_id={sid}", headers=admin()).json()
    assert again["code"] == first["code"]

    new = client.post(f"/api/admin/line/checkin-qr/rotate?session_id={sid}", headers=admin()).json()
    assert new["code"] != first["code"]
    old = client.get(f"/api/line/checkin?c={first['code']}", headers=member(BAM, "Bam")).json()
    assert old["state"] == "expired"
    assert (
        client.get(f"/api/line/checkin?c={new['code']}", headers=member(BAM, "Bam")).json()["state"]
        == "ready"
    )


def test_a_linked_member_checks_themselves_in_once(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    code = client.get(f"/api/admin/line/checkin-qr?session_id={sid}", headers=admin()).json()[
        "code"
    ]

    ready = client.get(f"/api/line/checkin?c={code}", headers=member(BAM, "Bam")).json()
    assert ready["state"] == "ready" and ready["player"]["nickname"] == "Bam"
    assert ready["night"]["location"] == "KB court"
    done = client.post("/api/line/checkin", json={"code": code}, headers=member(BAM, "Bam")).json()
    assert done["state"] == "in" and done["checkin_time"]
    twice = client.post("/api/line/checkin", json={"code": code}, headers=member(BAM, "Bam")).json()
    assert twice["state"] == "in"
    rows_ = [c for c in db.tables["checkins"] if c["session_id"] == sid]
    assert len(rows_) == 1 and rows_[0]["via"] == "line"

    # The admin sees who came in through LINE.
    listed = client.get(f"/api/admin/checkins?session_id={sid}", headers=admin()).json()
    assert [c["via"] for c in listed] == ["line"]


def test_only_tonights_open_night_and_only_linked_members(
    client: TestClient, db: MiniSupabase
) -> None:
    sid = night(db)
    code = client.get(f"/api/admin/line/checkin-qr?session_id={sid}", headers=admin()).json()[
        "code"
    ]
    # Not linked to anyone in the club: nothing to check in.
    stranger = client.post("/api/line/checkin", json={"code": code}, headers=member(BALL)).json()
    assert stranger["state"] == "unlinked"
    assert not db.tables.get("checkins")
    # Nonsense or unknown codes, and an admin token, get nowhere.
    assert (
        client.get("/api/line/checkin?c=%27%20or%201=1", headers=member(BAM)).json()["state"]
        == "expired"
    )
    assert (
        client.get("/api/line/checkin?c=" + "x" * 16, headers=member(BAM)).json()["state"]
        == "expired"
    )
    assert client.post("/api/line/checkin", json={"code": code}, headers=admin()).status_code == 401

    # A QR from an old night still open, or from a closed night, checks nobody in.
    old = night(db, days_ago=3)
    old_code = client.get(f"/api/admin/line/checkin-qr?session_id={old}", headers=admin()).json()[
        "code"
    ]
    assert (
        client.get(f"/api/line/checkin?c={old_code}", headers=member(BAM)).json()["state"]
        == "expired"
    )
    late = night(db, days_ago=1)
    late_code = client.get(f"/api/admin/line/checkin-qr?session_id={late}", headers=admin()).json()[
        "code"
    ]
    assert (
        client.get(f"/api/line/checkin?c={late_code}", headers=member(BAM)).json()["state"]
        == "ready"
    )
    next(s for s in db.tables["sessions"] if s["id"] == sid)["status"] = "closed"
    assert (
        client.post("/api/line/checkin", json={"code": code}, headers=member(BAM)).json()["state"]
        == "expired"
    )
    assert (
        client.get(f"/api/admin/line/checkin-qr?session_id={sid}", headers=admin()).status_code
        == 409
    )


# --- checking out, paying, and the member's own bills ------------------------


def match(
    db: MiniSupabase, sid: str, players: list[str], status: str = "completed"
) -> dict[str, Any]:
    row = {
        "id": str(uuid4()),
        "session_id": sid,
        "type": "double",
        "team1_player_ids": players[:2],
        "team2_player_ids": players[2:],
        "status": status,
        "created_at": "2026-01-01T00:00:00Z",
    }
    db.tables.setdefault("matches", []).append(row)
    return row


def settings(db: MiniSupabase) -> None:
    db.tables["club_settings"] = [
        {
            "id": 1,
            "promptpay_id": "0812345678",
            "promptpay_type": "phone",
            "payment_method": "promptpay",
            "bank_name": None,
            "bank_account_number": None,
            "bank_account_name": None,
            "uploaded_qr_url": None,
        }
    ]


def test_check_out_pay_and_have_the_slip_checked(client: TestClient, db: MiniSupabase) -> None:
    settings(db)
    sid = night(db)
    bam, ball, bank = pid(db, "Bam"), pid(db, "Ball"), pid(db, "Bank")
    client.post("/api/admin/checkins", json={"session_id": sid, "player_id": bam}, headers=admin())
    match(db, sid, [bam, ball, bank, ball])
    match(db, sid, [bam, bank, ball, bank])
    now = client.get("/api/line/tonight", headers=member(BAM)).json()
    assert (now["state"], now["games"], now["amount"], now["busy"]) == ("in", 2, 80 + 2 * 29, False)

    playing = match(db, sid, [bam, ball, bank, ball], status="in_progress")
    assert client.get("/api/line/tonight", headers=member(BAM)).json()["busy"] is True
    refused = client.post("/api/line/checkout", json={"session_id": sid}, headers=member(BAM))
    assert refused.status_code == 409
    playing["status"] = "completed"

    out = client.post("/api/line/checkout", json={"session_id": sid}, headers=member(BAM)).json()
    assert out["state"] == "out" and out["bill"]["amount"] == 80 + 3 * 29
    assert all(c["checkout_time"] for c in db.tables["checkins"] if c["player_id"] == bam)
    bill_id = out["bill"]["id"]

    pay = client.get(f"/api/line/bills/{bill_id}/pay", headers=member(BAM)).json()
    assert pay["method"] == "promptpay" and pay["amount"] == 167 and pay["data_uri"]
    assert pay["qr_modules"] and len(pay["qr_modules"]) == len(pay["qr_modules"][0])
    # Nobody else can see or pay it.
    next(p for p in db.tables["players"] if p["nickname"] == "Bank")["line_user_id"] = BANK
    assert client.get(f"/api/line/bills/{bill_id}/pay", headers=member(BANK)).status_code == 404

    sent = client.post(
        f"/api/line/bills/{bill_id}/slip",
        files={"file": ("s.png", _png(), "image/png")},
        headers=member(BAM),
    ).json()
    assert sent["slip_url"] and sent["paid_status"] == "unpaid"
    mine = client.get("/api/line/bills", headers=member(BAM)).json()
    assert mine["due"] == 0  # waiting on the admin, not owed
    assert [b["id"] for b in mine["bills"]] == [bill_id]

    # The admin sees the slip on the bill, refuses it; the member is asked again.
    listed = client.get(f"/api/admin/billing?session_id={sid}", headers=admin()).json()
    assert listed[0]["slip_url"] == sent["slip_url"]
    refused_slip = client.post(f"/api/admin/billing/{bill_id}/reject-slip", headers=admin()).json()
    assert refused_slip["slip_url"] is None and refused_slip["slip_rejected_at"]
    assert db.storage_files == {}
    again = client.get("/api/line/bills", headers=member(BAM)).json()
    assert again["due"] == 167 and again["bills"][0]["slip_rejected_at"]

    client.post(
        f"/api/line/bills/{bill_id}/slip",
        files={"file": ("s.png", _png(), "image/png")},
        headers=member(BAM),
    )
    client.patch(
        f"/api/admin/billing/{bill_id}/paid-status", json={"paid_status": "paid"}, headers=admin()
    )
    assert (
        client.get("/api/line/bills", headers=member(BAM)).json()["bills"][0]["paid_status"]
        == "paid"
    )
    assert client.get(f"/api/line/bills/{bill_id}/pay", headers=member(BAM)).status_code == 409


def test_a_free_night_and_a_forgotten_checkout(client: TestClient, db: MiniSupabase) -> None:
    settings(db)
    bam = pid(db, "Bam")
    # Never played: checking out costs nothing, and there is nothing to pay.
    sid = night(db)
    client.post("/api/admin/checkins", json={"session_id": sid, "player_id": bam}, headers=admin())
    out = client.post("/api/line/checkout", json={"session_id": sid}, headers=member(BAM)).json()
    assert out["bill"]["amount"] == 0
    assert (
        client.get(f"/api/line/bills/{out['bill']['id']}/pay", headers=member(BAM)).status_code
        == 409
    )

    # Forgot to check out: the admin closes the night, and the bill is theirs to pay later.
    late = night(db, days_ago=1)
    client.post("/api/admin/checkins", json={"session_id": late, "player_id": bam}, headers=admin())
    match(db, late, [bam, pid(db, "Ball"), pid(db, "Bank"), pid(db, "Ball")])
    client.post(f"/api/admin/billing/close-session/{late}", headers=admin())
    assert client.get("/api/line/tonight", headers=member(BAM)).json()["state"] in ("out", "none")
    mine = client.get("/api/line/bills", headers=member(BAM)).json()
    assert mine["due"] == 80 + 29
    assert (
        client.post(
            "/api/line/checkout", json={"session_id": late}, headers=member(BAM)
        ).status_code
        == 409
    )


def test_checkout_is_for_linked_members_checked_in_tonight(
    client: TestClient, db: MiniSupabase
) -> None:
    sid = night(db)
    assert client.get("/api/line/tonight", headers=member(BALL)).status_code == 403
    assert client.get("/api/line/bills", headers=member(BALL)).status_code == 403
    assert client.get("/api/line/tonight", headers=member(BAM)).json()["state"] == "none"
    assert (
        client.post("/api/line/checkout", json={"session_id": sid}, headers=member(BAM)).status_code
        == 409
    )
    assert (
        client.post("/api/line/checkout", json={"session_id": sid}, headers=admin()).status_code
        == 401
    )


def test_line_sign_ins_are_throttled(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers import line as line_router

    line_router.reset_throttle()
    monkeypatch.setattr(line_router, "SESSIONS_PER_WINDOW", 3)
    monkeypatch.setattr(
        line_auth,
        "verify_id_token",
        lambda token, http=None: line_auth.LineProfile(user_id=BALL, name="บอล", picture=None),
    )
    codes = [
        client.post("/api/line/session", json={"id_token": "x" * 40}).status_code for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]
    line_router.reset_throttle()


def test_tonight_ignores_old_closed_nights(client: TestClient, db: MiniSupabase) -> None:
    bam = pid(db, "Bam")
    for days in range(5, 40):
        old = night(db, days_ago=days, status="closed")
        db.tables.setdefault("checkins", []).append(
            {
                "id": str(uuid4()),
                "session_id": old,
                "player_id": bam,
                "checkin_time": "2026-01-01T00:00:00Z",
                "checkout_time": "2026-01-01T03:00:00Z",
                "via": "admin",
            }
        )
    assert client.get("/api/line/tonight", headers=member(BAM)).json()["state"] == "none"
    sid = night(db)
    client.post("/api/admin/checkins", json={"session_id": sid, "player_id": bam}, headers=admin())
    now = client.get("/api/line/tonight", headers=member(BAM)).json()
    assert now["state"] == "in" and now["night"]["id"] == sid


def test_everyone_sees_who_is_linked_but_never_their_line(
    client: TestClient, db: MiniSupabase
) -> None:
    db.tables["players"][2]["line_name"] = "Bam LINE"
    rows = client.get("/api/players").json()
    listed = {r.get("player", r)["nickname"]: r.get("player", r) for r in rows}
    assert listed["Bam"]["line_linked"] is True
    assert listed["Ball"]["line_linked"] is False
    one = client.get(f"/api/players/{pid(db, 'Bam')}").json()
    assert one["line_linked"] is True
    for p in [*listed.values(), one]:
        assert "line_user_id" not in p and "line_name" not in p


def test_the_invite_qr_opens_the_line_page(client: TestClient, db: MiniSupabase) -> None:
    assert client.get("/api/admin/line/invite").status_code == 401
    got = client.get("/api/admin/line/invite", headers=admin()).json()
    assert got["url"] == "https://liff.line.me/1234567890-AbCdEfGh"
    assert got["qr_modules"] and set("".join(got["qr_modules"])) <= {"0", "1"}


def test_no_invite_qr_until_line_is_set_up(
    client: TestClient, db: MiniSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "line_liff_id", None)
    assert client.get("/api/admin/line/invite", headers=admin()).status_code == 503


# --- checking in by where the phone is ----------------------------------------

from app.services import line_gps

COURT = (13.7563, 100.5018)


def _away(metres: float) -> tuple[float, float]:
    """A point this many metres north of the court."""
    return COURT[0] + metres / 111_195, COURT[1]


def _fix(metres: float = 0, accuracy: float = 10) -> dict[str, float]:
    lat, lng = _away(metres)
    return {"lat": lat, "lng": lng, "accuracy": accuracy}


def _pin(client: TestClient, sid: str, radius: int = 100, accuracy: float = 8) -> Any:
    body = {"lat": COURT[0], "lng": COURT[1], "accuracy": accuracy, "radius_m": radius}
    return client.put(f"/api/admin/line/checkin-spot?session_id={sid}", json=body, headers=admin())


def test_distance_is_metres() -> None:
    assert abs(line_gps.distance_m(*COURT, *_away(100)) - 100) < 1
    assert line_gps.inside(120, 100, 30) and not line_gps.inside(160, 100, 300)


def test_admin_pins_reads_and_unpins_tonight(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    assert client.get(f"/api/admin/line/checkin-spot?session_id={sid}", headers=admin()).json() is None
    spot = _pin(client, sid, radius=80).json()
    assert spot["radius_m"] == 80 and spot["accuracy_m"] == 8 and spot["pinned_at"]
    read = client.get(f"/api/admin/line/checkin-spot?session_id={sid}", headers=admin()).json()
    assert read["lat"] == COURT[0]
    assert client.delete(f"/api/admin/line/checkin-spot?session_id={sid}", headers=admin()).status_code == 204
    assert client.get(f"/api/admin/line/checkin-spot?session_id={sid}", headers=admin()).json() is None


def test_pin_is_refused_when_wrong(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    assert _pin(client, sid, accuracy=900).status_code == 422  # GPS too unsure
    assert _pin(client, sid, radius=5).status_code == 422
    assert _pin(client, sid, radius=5000).status_code == 422
    bad = {"lat": 123, "lng": 0, "accuracy": 5}
    assert client.put(f"/api/admin/line/checkin-spot?session_id={sid}", json=bad, headers=admin()).status_code == 422
    closed = night(db, status="closed")
    assert _pin(client, closed).status_code == 409
    assert _pin(client, str(uuid4())).status_code == 404
    body = {"lat": COURT[0], "lng": COURT[1], "accuracy": 5}
    assert client.put(f"/api/admin/line/checkin-spot?session_id={sid}", json=body, headers=member(BAM)).status_code == 401


def test_member_inside_the_circle_is_checked_in(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    _pin(client, sid, radius=100)
    done = client.post("/api/line/checkin/nearby", json=_fix(60), headers=member(BAM, "Bam")).json()
    assert done["state"] == "in" and done["checkin_time"] and done["player"]["nickname"] == "Bam"
    again = client.post("/api/line/checkin/nearby", json=_fix(10), headers=member(BAM, "Bam")).json()
    assert again["state"] == "in" and again["checkin_time"] == done["checkin_time"]
    mine = [c for c in db.tables["checkins"] if c["session_id"] == sid]
    assert len(mine) == 1 and mine[0]["via"] == "gps"
    listed = client.get(f"/api/admin/checkins?session_id={sid}", headers=admin()).json()
    assert listed[0]["via"] == "gps"


def test_member_outside_or_unsure_is_not(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    _pin(client, sid, radius=100)
    far = client.post("/api/line/checkin/nearby", json=_fix(400), headers=member(BAM)).json()
    assert far["state"] == "far" and 395 <= far["distance_m"] <= 405 and far["radius_m"] == 100
    # an unsure phone only gets a little slack: 140 m away, ±500 m, is not in
    weak = client.post("/api/line/checkin/nearby", json=_fix(140, accuracy=500), headers=member(BAM)).json()
    assert weak["state"] == "weak"
    edge = client.post("/api/line/checkin/nearby", json=_fix(170, accuracy=200), headers=member(BAM)).json()
    assert edge["state"] == "far"
    assert not db.tables.get("checkins")
    # slack of up to 50 m for an unsure phone just outside
    near = client.post("/api/line/checkin/nearby", json=_fix(140, accuracy=60), headers=member(BAM)).json()
    assert near["state"] == "in"


def test_nobody_is_checked_in_without_a_pin_or_a_link(client: TestClient, db: MiniSupabase) -> None:
    night(db)  # open, never pinned
    none = client.post("/api/line/checkin/nearby", json=_fix(0), headers=member(BAM)).json()
    assert none["state"] == "none"
    sid = night(db)
    _pin(client, sid)
    stranger = client.post("/api/line/checkin/nearby", json=_fix(0), headers=member(BALL)).json()
    assert stranger["state"] == "unlinked" and stranger["player"] is None
    assert not db.tables.get("checkins")
    assert client.post("/api/line/checkin/nearby", json=_fix(0), headers=admin()).status_code == 401
    nan = {"lat": "NaN", "lng": 0, "accuracy": 5}
    assert client.post("/api/line/checkin/nearby", json=nan, headers=member(BAM)).status_code == 422


def test_old_and_closed_nights_check_nobody_in(client: TestClient, db: MiniSupabase) -> None:
    sid = night(db)
    _pin(client, sid)
    db.tables["sessions"][-1]["status"] = "closed"
    assert client.post("/api/line/checkin/nearby", json=_fix(0), headers=member(BAM)).json()["state"] == "none"
    old = night(db, days_ago=3)
    _pin(client, old)
    assert client.post("/api/line/checkin/nearby", json=_fix(0), headers=member(BAM)).json()["state"] == "none"


def test_the_nearest_pinned_night_is_used(client: TestClient, db: MiniSupabase) -> None:
    far_night, near_night = night(db), night(db)
    body = {"lat": COURT[0] + 0.05, "lng": COURT[1], "accuracy": 5, "radius_m": 100}
    client.put(f"/api/admin/line/checkin-spot?session_id={far_night}", json=body, headers=admin())
    _pin(client, near_night)
    client.post("/api/line/checkin/nearby", json=_fix(0), headers=member(BAM))
    assert [c["session_id"] for c in db.tables["checkins"]] == [near_night]
