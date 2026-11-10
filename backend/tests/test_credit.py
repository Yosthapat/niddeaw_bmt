"""Club credit: topping up from LINE, the admin's check, balances that can't
go below zero or be credited twice, and the money the dashboard counts.

Runs against the uxlab's in-memory database (tools/uxlab/minisupabase.py),
which applies filters and the credit tables' constraints, because what is
being tested is which rows a compare-and-swap finds."""

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
from app.services import credit_card_service, credit_service

BALL = "U" + "a" * 32
BANK = "U" + "b" * 32
ADMIN_ID = str(uuid4())


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
    fake = MiniSupabase(
        {
            "players": [player("Ball", 1, line_user_id=BALL), player("Bank", 2, line_user_id=BANK), player("Bam", 3)],
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "credit_packages": [
                {"id": str(uuid4()), "credits": 1000, "price": 950, "is_active": True, "sort_order": 0},
                {"id": str(uuid4()), "credits": 5000, "price": 4500, "is_active": True, "sort_order": 1},
                {"id": str(uuid4()), "credits": 300, "price": 300, "is_active": False, "sort_order": 2},
            ],
            "club_settings": [
                {"id": 1, "payment_method": "promptpay", "promptpay_id": "0812345678", "promptpay_type": "phone",
                 "bank_name": None, "bank_account_number": None, "bank_account_name": None, "uploaded_qr_url": None,
                 "default_court_fee_per_person": 80, "default_shuttlecock_price_per_game": 29},
            ],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    credit_card_service.invalidate()
    yield fake
    app.dependency_overrides.pop(get_supabase, None)
    credit_card_service.invalidate()


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, nickname: str) -> str:
    return next(str(p["id"]) for p in db.tables["players"] if p["nickname"] == nickname)


def package(db: MiniSupabase, credits: int) -> str:
    return next(str(p["id"]) for p in db.tables["credit_packages"] if p["credits"] == credits)


def topped_up(client: TestClient, db: MiniSupabase, credits: int = 1000) -> str:
    """Ball picks a package and sends the slip; returns the top-up id."""
    state = client.post("/api/line/credit/topups", json={"package_id": package(db, credits)}, headers=member()).json()
    topup = state["pending"]["id"]
    res = client.post(f"/api/line/credit/topups/{topup}/slip", files={"file": ("s.jpg", slip(), "image/jpeg")}, headers=member())
    assert res.status_code == 200, res.text
    return str(topup)


def test_a_member_sees_only_the_packages_on_sale(client: TestClient) -> None:
    state = client.get("/api/line/credit", headers=member()).json()
    assert state["balance"] == 0
    assert [(p["credits"], p["price"]) for p in state["packages"]] == [(1000, 950), (5000, 4500)]


def test_an_unlinked_line_account_has_no_credit(client: TestClient) -> None:
    assert client.get("/api/line/credit", headers=member("U" + "f" * 32)).status_code == 403


def test_top_up_pay_and_approve(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db)
    pay = client.get(f"/api/line/credit/topups/{topup}/pay", headers=member()).json()
    assert pay["amount"] == 950
    # The admin sees it waiting, approves it, and the credit arrives.
    waiting = client.get("/api/admin/credit/topups", headers=admin()).json()
    assert [(w["player_nickname"], w["credits"], w["price"]) for w in waiting] == [("Ball", 1000, 950)]
    assert client.post(f"/api/admin/credit/topups/{topup}/approve", headers=admin()).status_code == 200
    state = client.get("/api/line/credit", headers=member()).json()
    assert state["balance"] == 1000 and state["pending"] is None
    assert [(h["kind"], h["delta"], h["balance_after"], h["cash"]) for h in state["history"]] == [("topup", 1000, 1000, 950)]


def test_approving_twice_credits_once(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db)
    assert client.post(f"/api/admin/credit/topups/{topup}/approve", headers=admin()).status_code == 200
    assert client.post(f"/api/admin/credit/topups/{topup}/approve", headers=admin()).status_code == 409
    assert credit_service.balance(db, pid(db, "Ball")) == 1000  # type: ignore[arg-type]
    assert len(db.tables["credit_ledger"]) == 1


def test_no_approving_before_a_slip(client: TestClient, db: MiniSupabase) -> None:
    state = client.post("/api/line/credit/topups", json={"package_id": package(db, 1000)}, headers=member()).json()
    res = client.post(f"/api/admin/credit/topups/{state['pending']['id']}/approve", headers=admin())
    assert res.status_code == 409
    assert credit_service.balance(db, pid(db, "Ball")) == 0  # type: ignore[arg-type]


def test_rejected_slip_credits_nothing_and_says_why(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db)
    res = client.post(f"/api/admin/credit/topups/{topup}/reject", json={"note": "ยอดในสลิปไม่ตรง"}, headers=admin())
    assert res.status_code == 200
    state = client.get("/api/line/credit", headers=member()).json()
    assert state["balance"] == 0 and state["pending"] is None
    assert state["rejected"]["note"] == "ยอดในสลิปไม่ตรง"


def test_picking_again_swaps_the_package_until_a_slip_is_sent(client: TestClient, db: MiniSupabase) -> None:
    client.post("/api/line/credit/topups", json={"package_id": package(db, 1000)}, headers=member())
    state = client.post("/api/line/credit/topups", json={"package_id": package(db, 5000)}, headers=member()).json()
    assert (state["pending"]["credits"], state["pending"]["price"]) == (5000, 4500)
    assert len(db.tables["credit_topups"]) == 1
    client.post(f"/api/line/credit/topups/{state['pending']['id']}/slip", files={"file": ("s.jpg", slip(), "image/jpeg")}, headers=member())
    again = client.post("/api/line/credit/topups", json={"package_id": package(db, 1000)}, headers=member())
    assert again.status_code == 409


def test_an_inactive_package_cannot_be_bought(client: TestClient, db: MiniSupabase) -> None:
    res = client.post("/api/line/credit/topups", json={"package_id": package(db, 300)}, headers=member())
    assert res.status_code == 404


def test_someone_elses_top_up_is_not_found(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db)
    assert client.get(f"/api/line/credit/topups/{topup}/pay", headers=member(BANK)).status_code == 404
    assert client.delete(f"/api/line/credit/topups/{topup}", headers=member(BANK)).status_code == 404


def test_cancel_before_the_admin_looks(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db)
    state = client.delete(f"/api/line/credit/topups/{topup}", headers=member()).json()
    assert state["pending"] is None and db.tables["credit_topups"] == []


def test_adjust_needs_a_reason_and_never_goes_below_zero(client: TestClient, db: MiniSupabase) -> None:
    ball = pid(db, "Ball")
    url = f"/api/admin/credit/players/{ball}/adjust"
    assert client.post(url, json={"delta": 500, "note": ""}, headers=admin()).status_code == 422
    res = client.post(url, json={"delta": 500, "cash": 500, "note": "รับเงินสดที่สนาม"}, headers=admin())
    assert res.status_code == 200 and res.json()["balance"] == 500
    too_much = client.post(url, json={"delta": -600, "note": "คืนเงิน"}, headers=admin())
    assert too_much.status_code == 409
    assert client.post(url, json={"delta": -200, "cash": 190, "note": "คืนเงิน ย้ายก๊วน"}, headers=admin()).json()["balance"] == 300


def test_two_spends_at_once_cannot_both_use_the_same_credit(db: MiniSupabase) -> None:
    ball = pid(db, "Ball")
    credit_service.apply(db, ball, 500, "adjust", note="seed")  # type: ignore[arg-type]
    real_select = db.table

    # The second spend reads the balance before the first one writes it.
    seen: list[int] = []

    def racing(name: str) -> Any:
        q = real_select(name)
        if name == "player_credits" and not seen:
            seen.append(1)
            credit_service.apply(db, ball, -400, "bill", note="first")  # type: ignore[arg-type]
        return q

    db.table = racing  # type: ignore[method-assign]
    with pytest.raises(credit_service.NotEnoughCredit):
        credit_service.apply(db, ball, -400, "bill", note="second")  # type: ignore[arg-type]
    db.table = real_select  # type: ignore[method-assign]
    assert credit_service.balance(db, ball) == 100  # type: ignore[arg-type]


def test_balances_and_summary_for_the_admin(client: TestClient, db: MiniSupabase) -> None:
    topup = topped_up(client, db, 5000)
    client.post(f"/api/admin/credit/topups/{topup}/approve", headers=admin())
    bank = pid(db, "Bank")
    client.post(f"/api/admin/credit/players/{bank}/adjust", json={"delta": 300, "cash": 300, "note": "เงินสด"}, headers=admin())
    client.post(f"/api/admin/credit/players/{bank}/adjust", json={"delta": -100, "cash": 100, "note": "คืนเงิน"}, headers=admin())
    client.post(f"/api/admin/credit/players/{bank}/adjust", json={"delta": 50, "note": "ชดเชยบิลผิด"}, headers=admin())
    bal = client.get("/api/admin/credit/balances", headers=admin()).json()
    assert bal["outstanding"] == 5250
    assert [(m["nickname"], m["balance"]) for m in bal["members"]] == [("Ball", 5000), ("Bank", 250)]
    s = client.get("/api/admin/credit/summary", headers=admin()).json()
    # Cash that moved: 4,500 + 300 in, 100 back out; the 50 goodwill moved none.
    assert (s["cash_in"], s["cash_out"], s["outstanding"]) == (4800, 100, 5250)
    assert sum(d["cash"] for d in s["daily"]) == 4700


def test_packages_can_be_managed(client: TestClient, db: MiniSupabase) -> None:
    res = client.post("/api/admin/credit/packages", json={"credits": 2000, "price": 1850}, headers=admin())
    assert res.status_code == 201
    new = res.json()["id"]
    assert client.post("/api/admin/credit/packages", json={"credits": 100, "price": 120}, headers=admin()).status_code == 422
    assert client.patch(f"/api/admin/credit/packages/{new}", json={"price": 2500}, headers=admin()).status_code == 422
    assert client.patch(f"/api/admin/credit/packages/{new}", json={"is_active": False}, headers=admin()).json()["is_active"] is False
    assert client.delete(f"/api/admin/credit/packages/{new}", headers=admin()).status_code == 204


def test_admin_routes_need_an_admin(client: TestClient, db: MiniSupabase) -> None:
    for method, url in [("get", "/api/admin/credit/topups"), ("get", "/api/admin/credit/balances"), ("get", "/api/admin/credit/summary")]:
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers=member()).status_code == 401


# --- the pink and black cards (services/credit_card_service.py) ---------------


def _row(n: int, delta: int, after: int, kind: str = "topup", ref: str | None = None) -> dict[str, Any]:
    return {
        "id": f"r{n}", "player_id": "p", "delta": delta, "balance_after": after, "kind": kind,
        "ref_id": ref, "created_at": f"2026-11-{n:02d}T10:00:00Z",
    }


def test_a_card_lasts_while_the_credit_does() -> None:
    line = {"t1", "t2", "t3", "t4"}
    run = [_row(1, 1000, 1000, ref="t1")]
    assert credit_card_service.cards_from(run, line)["p"].tier == "pink"
    # the grandest pack in the run counts: 5,000 then 1,000 is still black
    run += [_row(2, 5000, 6000, ref="t2"), _row(3, 1000, 7000, ref="t3")]
    assert credit_card_service.cards_from(run, line)["p"].tier == "black"
    assert credit_card_service.cards_from(run, line)["p"].since == "r2"
    # spent down to nothing: the card goes
    run += [_row(4, -7000, 0, kind="bill")]
    assert credit_card_service.cards_from(run, line) == {}
    # cash at the court keeps credit but earns no card; a LINE pack does
    run += [_row(5, 2000, 2000, ref=None)]
    assert credit_card_service.cards_from(run, line) == {}
    run += [_row(6, 1000, 3000, ref="t4")]
    assert credit_card_service.cards_from(run, line)["p"].tier == "pink" and credit_card_service.cards_from(run, line)["p"].since == "r6"
    # a pack smaller than 1,000 is no card
    assert credit_card_service.cards_from([_row(1, 500, 500, ref="t1")], line) == {}


def test_cards_from_packs_bought_in_line(client: TestClient, db: MiniSupabase) -> None:
    ball = pid(db, "Ball")
    assert client.get("/api/credit-cards").json() == {}
    assert client.get("/api/line/credit", headers=member()).json()["card"] is None
    client.post(f"/api/admin/credit/topups/{topped_up(client, db)}/approve", headers=admin())
    assert client.get("/api/credit-cards").json() == {ball: "pink"}
    pink = client.get("/api/line/credit", headers=member()).json()["card"]
    assert pink["tier"] == "pink" and pink["since"]

    adjust = f"/api/admin/credit/players/{ball}/adjust"
    client.post(adjust, json={"delta": -1000, "cash": 950, "note": "คืนเงิน"}, headers=admin())
    assert client.get("/api/credit-cards").json() == {}
    # cash at the court: credit, but no card
    client.post(adjust, json={"delta": 1000, "cash": 1000, "note": "รับเงินสดที่สนาม"}, headers=admin())
    assert client.get("/api/credit-cards").json() == {}

    client.post(f"/api/admin/credit/topups/{topped_up(client, db, 5000)}/approve", headers=admin())
    assert client.get("/api/credit-cards").json() == {ball: "black"}
    black = client.get("/api/line/credit", headers=member()).json()["card"]
    assert black["tier"] == "black" and black["since"] != pink["since"]


def test_packages_list_cheapest_first_whenever_added(client: TestClient, db: MiniSupabase) -> None:
    # added last, with a later sort_order, a cheaper pack still comes first
    res = client.post("/api/admin/credit/packages", json={"credits": 500, "price": 500, "sort_order": 9}, headers=admin())
    assert res.status_code == 201
    # same price as another: the bigger pack goes first
    res = client.post("/api/admin/credit/packages", json={"credits": 520, "price": 500}, headers=admin())
    assert res.status_code == 201
    listed = [(p["price"], p["credits"]) for p in client.get("/api/admin/credit/packages", headers=admin()).json()]
    assert [p for p, _ in listed] == sorted(p for p, _ in listed)
    assert listed.index((500, 520)) < listed.index((500, 500)) < listed.index((950, 1000))
    shown = [p["price"] for p in client.get("/api/line/credit", headers=member()).json()["packages"]]
    assert shown == sorted(shown) and shown.index(500) < shown.index(950)
