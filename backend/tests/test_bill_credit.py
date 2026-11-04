"""Paying a night's bill with club credit: all of it when the balance
covers it, part of it with the rest by transfer, never twice, given back
when the admin undoes a payment or the bill comes out smaller — and the
dues money counted without the credit's baht a second time."""

import io
import os
import sys
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token
from app.services import credit_service

BALL = "U" + "a" * 32
BANK = "U" + "b" * 32
ADMIN_ID = str(uuid4())
NIGHT = str(uuid4())


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


def member(user_id: str = BALL) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(user_id, 'LINE name')}"}


def player(nickname: str, seq: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(uuid4()), "nickname": nickname, "member_seq": seq, "elo_score": 1000,
        "elo_level": "beer", "is_active": True, "created_at": "2026-01-01T00:00:00Z", **extra,
    }


def slip() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (600, 1000), (240, 240, 240)).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    ball = player("Ball", 1, line_user_id=BALL)
    bank = player("Bank", 2, line_user_id=BANK)
    fake = MiniSupabase(
        {
            "players": [ball, bank],
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "sessions": [
                {"id": NIGHT, "date": "2026-11-06", "location": "KB", "court_fee_per_person": 80,
                 "shuttlecock_price_per_game": 29, "status": "closed", "created_by": ADMIN_ID,
                 "created_at": "2026-11-06T12:00:00Z", "line_checkin_code": None},
            ],
            "billings": [
                {"id": str(uuid4()), "session_id": NIGHT, "player_id": ball["id"], "game_count": 3,
                 "amount_calc": 167, "updated_at": "2026-11-06T15:00:00Z"},
                {"id": str(uuid4()), "session_id": NIGHT, "player_id": bank["id"], "game_count": 2,
                 "amount_calc": 138, "updated_at": "2026-11-06T15:00:00Z"},
            ],
            "club_settings": [
                {"id": 1, "payment_method": "promptpay", "promptpay_id": "0812345678", "promptpay_type": "phone",
                 "bank_name": None, "bank_account_number": None, "bank_account_name": None, "uploaded_qr_url": None,
                 "default_court_fee_per_person": 80, "default_shuttlecock_price_per_game": 29},
            ],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, nickname: str) -> str:
    return next(str(p["id"]) for p in db.tables["players"] if p["nickname"] == nickname)


def bill(db: MiniSupabase, nickname: str) -> dict[str, Any]:
    return next(b for b in db.tables["billings"] if b["player_id"] == pid(db, nickname))


def give(db: MiniSupabase, nickname: str, credits: int, cash: float | None = None) -> None:
    credit_service.apply(db, pid(db, nickname), credits, "topup", cash=cash if cash is not None else credits)  # type: ignore[arg-type]


def bal(db: MiniSupabase, nickname: str) -> int:
    return credit_service.balance(db, pid(db, nickname))  # type: ignore[arg-type]


def test_enough_credit_pays_the_whole_bill(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000, 950)
    res = client.post(f"/api/line/bills/{bill(db, 'Ball')['id']}/credit", headers=member())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["balance"] == 833
    assert (body["bill"]["paid_status"], body["bill"]["credit_used"], body["bill"]["left"]) == ("paid", 167, 0)
    spent = [e for e in db.tables["credit_ledger"] if e["kind"] == "bill"]
    assert [(e["delta"], e["cash"], e["ref_id"]) for e in spent] == [(-167, None, bill(db, "Ball")["id"])]
    # Nothing left to transfer, so there's no QR to show and no slip to send.
    assert client.get(f"/api/line/bills/{bill(db, 'Ball')['id']}/pay", headers=member()).status_code == 409


def test_short_credit_pays_part_and_the_qr_asks_for_the_rest(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 100)
    b = bill(db, "Ball")["id"]
    body = client.post(f"/api/line/bills/{b}/credit", headers=member()).json()
    assert body["balance"] == 0
    assert (body["bill"]["paid_status"], body["bill"]["credit_used"], body["bill"]["left"]) == ("unpaid", 100, 67)
    assert client.get(f"/api/line/bills/{b}/pay", headers=member()).json()["amount"] == 67
    assert client.get("/api/line/bills", headers=member()).json()["due"] == 67
    # The rest by transfer: the slip, then the admin marks it paid.
    assert client.post(f"/api/line/bills/{b}/slip", files={"file": ("s.jpg", slip(), "image/jpeg")}, headers=member()).status_code == 200
    assert client.get(f"/api/admin/billing/{b}/payment-info", headers=admin()).json()["amount"] == 67
    assert client.patch(f"/api/admin/billing/{b}/paid-status", json={"paid_status": "paid"}, headers=admin()).json()["credit_used"] == 100


def test_no_credit_no_slip_twice(client: TestClient, db: MiniSupabase) -> None:
    b = bill(db, "Ball")["id"]
    assert client.post(f"/api/line/bills/{b}/credit", headers=member()).status_code == 409
    give(db, "Ball", 1000)
    client.post(f"/api/line/bills/{b}/slip", files={"file": ("s.jpg", slip(), "image/jpeg")}, headers=member())
    # A slip is waiting for the admin: credit isn't taken on top of it.
    assert client.post(f"/api/line/bills/{b}/credit", headers=member()).status_code == 409
    assert bal(db, "Ball") == 1000


def test_paying_twice_takes_credit_once(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000)
    b = bill(db, "Ball")["id"]
    assert client.post(f"/api/line/bills/{b}/credit", headers=member()).status_code == 200
    assert client.post(f"/api/line/bills/{b}/credit", headers=member()).status_code == 409
    assert bal(db, "Ball") == 833


def test_the_bill_moving_underneath_puts_the_credit_back(db: MiniSupabase) -> None:
    from app.services import bill_credit

    give(db, "Ball", 1000)
    row = dict(bill(db, "Ball"))
    bill(db, "Ball")["paid_status"] = "paid"  # the admin marked it paid a moment before
    with pytest.raises(Exception, match="409"):
        bill_credit.pay(db, row, "คืน 6/11")  # type: ignore[arg-type]
    assert bal(db, "Ball") == 1000
    assert [e["kind"] for e in db.tables["credit_ledger"]] == ["topup", "bill", "refund"]


def test_someone_elses_bill_is_not_found(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Bank", 1000)
    assert client.post(f"/api/line/bills/{bill(db, 'Ball')['id']}/credit", headers=member(BANK)).status_code == 404
    assert bal(db, "Bank") == 1000


def test_undoing_a_payment_gives_the_credit_back(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000)
    b = bill(db, "Ball")["id"]
    client.post(f"/api/line/bills/{b}/credit", headers=member())
    res = client.patch(f"/api/admin/billing/{b}/paid-status", json={"paid_status": "unpaid"}, headers=admin())
    assert (res.json()["paid_status"], res.json()["credit_used"]) == ("unpaid", 0)
    assert bal(db, "Ball") == 1000
    back = db.tables["credit_ledger"][-1]
    assert (back["kind"], back["delta"], back["admin_id"]) == ("refund", 167, ADMIN_ID)


def test_a_smaller_bill_gives_back_the_difference(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000)
    b = bill(db, "Ball")["id"]
    client.post(f"/api/line/bills/{b}/credit", headers=member())
    res = client.patch(f"/api/admin/billing/{b}/adjust", json={"amount_adjusted": 100}, headers=admin())
    assert (res.json()["paid_status"], res.json()["credit_used"]) == ("paid", 100)
    assert bal(db, "Ball") == 900


def test_satang_are_left_to_transfer(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000)
    bill(db, "Ball")["amount_adjusted"] = 167.5
    body = client.post(f"/api/line/bills/{bill(db, 'Ball')['id']}/credit", headers=member()).json()
    assert (body["bill"]["credit_used"], body["bill"]["left"], body["bill"]["paid_status"]) == (167, 0.5, "unpaid")


def test_dues_money_leaves_out_what_credit_paid(client: TestClient, db: MiniSupabase) -> None:
    give(db, "Ball", 1000, 950)
    client.post(f"/api/line/bills/{bill(db, 'Ball')['id']}/credit", headers=member())
    give(db, "Bank", 100)
    client.post(f"/api/line/bills/{bill(db, 'Bank')['id']}/credit", headers=member(BANK))
    day = client.get("/api/admin/billing/revenue", headers=admin()).json()[0]
    # Earned 167 + 138; credit paid 167 + 100; Bank still owes 38.
    assert (day["total_amount"], day["credit_amount"], day["paid_amount"], day["paid_cash"], day["unpaid_amount"]) == (
        305, 267, 167, 0, 38,
    )
