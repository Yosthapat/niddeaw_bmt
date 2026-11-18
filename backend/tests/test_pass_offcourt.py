"""Niddeaw Pass off the court: 5% off in the shop and free name printing,
only for a holder ordering for themselves from LINE; 5% off a tournament
entry."""

import io
import json
import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.routers.public import shop as public_shop
from app.security import create_access_token, create_line_token
from app.services import pass_service
from app.services import tournament_service as ts

NAMES = ["Ball", "Bank"]
LINE = {name: "U" + chr(ord("a") + i) * 32 for i, name in enumerate(NAMES)}
SHIRT = str(uuid4())
CAP = str(uuid4())


def line(name: str) -> dict[str, str]:
    return {"X-Line-Token": create_line_token(LINE[name], "LINE name")}


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    now = datetime.now(UTC)
    players = [
        {"id": str(uuid4()), "nickname": n, "member_seq": i + 1, "elo_score": 1000, "elo_level": "beer",
         "is_active": True, "line_user_id": LINE[n], "created_at": "2026-01-01T00:00:00Z"}
        for i, n in enumerate(NAMES)
    ]
    fake = MiniSupabase(
        {
            "admins": [],
            "players": players,
            "club_settings": [{"id": 1, "payment_method": "promptpay", "promptpay_id": "0812345678",
                               "promptpay_type": "phone"}],
            "products": [
                {"id": SHIRT, "name": "เสื้อก๊วน", "price": 350, "sale_type": "preorder", "sizes": ["M", "L"],
                 "size_prices": {}, "preorder_closes_on": (now + timedelta(days=9)).date().isoformat(),
                 "image_urls": [], "is_active": True, "sort_order": 0, "created_at": "2026-11-01T00:00:00Z",
                 "name_print_price": 50},
                {"id": CAP, "name": "หมวก", "price": 200, "sale_type": "stock", "sizes": [], "size_prices": {},
                 "image_urls": [], "is_active": True, "sort_order": 1, "created_at": "2026-11-01T00:00:00Z"},
            ],
            "product_stock": [{"product_id": CAP, "size": "", "qty": 5}],
            "shop_orders": [],
            "shop_order_items": [],
            "slip_checks": [],
            # Ball holds a pass; Bank doesn't.
            "passes": [{"id": str(uuid4()), "player_id": players[0]["id"], "price": 249,
                        "starts_at": (now - timedelta(days=2)).isoformat(),
                        "ends_at": (now + timedelta(days=28)).isoformat(), "created_at": now.isoformat()}],
            "admin_activity_log": [],
        }
    )  # fmt: skip
    app.dependency_overrides[get_supabase] = lambda: fake
    public_shop.reset_throttle()
    yield fake
    app.dependency_overrides.pop(get_supabase, None)


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, name: str) -> str:
    return str(next(p["id"] for p in db.tables["players"] if p["nickname"] == name))


ITEMS: list[dict[str, Any]] = [
    {"product_id": SHIRT, "size": "M", "qty": 1, "print_name": "BALL"},
    {"product_id": CAP, "size": "", "qty": 1},
]


def slip() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (400, 700), (240, 240, 240)).save(out, format="JPEG")
    return out.getvalue()


def order(client: TestClient, buyer: str, headers: dict[str, str], **form: str) -> Any:
    return client.post(
        "/api/shop/orders",
        data={"items": json.dumps(ITEMS), "player_id": buyer, **form},
        files={"file": ("slip.jpg", slip(), "image/jpeg")},
        headers=headers,
    )


def test_percent_off_rounds_a_half_up() -> None:
    assert pass_service.percent_off(350, 5) == 18
    assert pass_service.percent_off(600, 5) == 30
    assert pass_service.percent_off(10, 5) == 1
    assert pass_service.percent_off(0, 5) == 0


def test_without_line_the_name_costs_and_nothing_comes_off(client: TestClient) -> None:
    q = client.post("/api/shop/quote", json={"items": ITEMS}).json()
    shirt = next(line for line in q["lines"] if line["print_name"])
    assert (shirt["print_price"], shirt["print_list_price"], shirt["line_total"]) == (50, 50, 400)
    assert (q["subtotal"], q["pass_discount"], q["total"], q["pass_applied"]) == (600, 0, 600, False)


def test_a_holder_from_line_prints_free_and_pays_five_percent_less(
    client: TestClient, db: MiniSupabase
) -> None:
    q = client.post(
        "/api/shop/quote", json={"items": ITEMS, "buyer_id": pid(db, "Ball")}, headers=line("Ball")
    ).json()
    shirt = next(line for line in q["lines"] if line["print_name"])
    assert (shirt["print_price"], shirt["print_list_price"], shirt["line_total"]) == (0, 50, 350)
    assert (q["subtotal"], q["pass_discount"], q["total"], q["pass_applied"]) == (550, 28, 522, True)
    pay = client.post(
        "/api/shop/payment", json={"items": ITEMS, "buyer_id": pid(db, "Ball")}, headers=line("Ball")
    ).json()
    assert pay["amount"] == 522


def test_no_pass_no_discount_even_from_line(client: TestClient, db: MiniSupabase) -> None:
    q = client.post(
        "/api/shop/quote", json={"items": ITEMS, "buyer_id": pid(db, "Bank")}, headers=line("Bank")
    ).json()
    assert (q["pass_applied"], q["total"]) == (False, 600)


def test_a_holder_buying_for_someone_else_gets_no_discount(
    client: TestClient, db: MiniSupabase
) -> None:
    q = client.post(
        "/api/shop/quote", json={"items": ITEMS, "buyer_id": pid(db, "Bank")}, headers=line("Ball")
    ).json()
    assert (q["pass_applied"], q["total"]) == (False, 600)
    # nor by naming the holder as buyer without their LINE
    r = order(client, pid(db, "Ball"), {}, expected_total="522")
    assert r.status_code == 409


def test_the_order_keeps_the_discount_and_the_name(client: TestClient, db: MiniSupabase) -> None:
    r = order(client, pid(db, "Ball"), line("Ball"), expected_total="522")
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["total"], body["pass_discount"]) == (522, 28)
    shirt = next(i for i in body["items"] if i["print_name"])
    assert (shirt["print_name"], shirt["print_price"], shirt["line_total"]) == ("BALL", 0, 350)
    tally = client.get("/api/admin/shop/preorder-tally", headers=admin()).json()
    assert tally[0]["print_names"] == [{"size": "M", "name": "BALL", "qty": 1}]


def test_an_expired_line_sign_in_refuses_rather_than_charging_more(
    client: TestClient, db: MiniSupabase
) -> None:
    r = order(client, pid(db, "Ball"), {"X-Line-Token": "expired"}, expected_total="522")
    assert r.status_code == 409
    assert "LINE" in r.json()["detail"]
    assert db.tables["shop_orders"] == []


def test_admin_editing_a_line_keeps_the_print_price_and_retakes_the_discount(
    client: TestClient, db: MiniSupabase
) -> None:
    body = order(client, pid(db, "Ball"), line("Ball"), expected_total="522").json()
    shirt = next(i for i in body["items"] if i["print_name"])
    r = client.patch(
        f"/api/admin/shop/orders/{body['id']}/items/{shirt['id']}", json={"qty": 2}, headers=admin()
    )
    assert r.status_code == 200, r.text
    # 2 × 350 (free print) + 200 = 900, less 45
    assert (r.json()["total"], r.json()["pass_discount"]) == (855, 45)


def test_a_name_on_a_product_that_prints_none_is_refused(client: TestClient) -> None:
    q = client.post(
        "/api/shop/quote", json={"items": [{"product_id": CAP, "qty": 1, "print_name": "X"}]}
    ).json()
    assert q["ok"] is False


def _tournament() -> dict[str, Any]:
    return {"id": str(uuid4()), "entry_fee": 600, "shuttle_fee": 100}


def test_a_holder_pays_five_percent_less_to_enter(db: MiniSupabase) -> None:
    db.tables.setdefault("tournament_teams", [])
    db.tables.setdefault("tournament_entrants", [])
    ball = next(p for p in db.tables["players"] if p["nickname"] == "Ball")
    bank = next(p for p in db.tables["players"] if p["nickname"] == "Bank")
    details = {"first_name": "a", "last_name": "b", "phone": "0812345678"}
    ts.create_team(db, _tournament(), str(uuid4()), "ทีม", (ball, details), (bank, details), "admin")  # type: ignore[arg-type]
    ents = {e["player_id"]: e for e in db.tables["tournament_entrants"]}
    # 700 split 350 / 350; Ball's 350 less 18
    assert (ents[ball["id"]]["share"], ents[ball["id"]]["pass_off"]) == (332, 18)
    assert (ents[bank["id"]]["share"], ents[bank["id"]].get("pass_off", 0)) == (350, 0)


def test_a_pass_bought_after_signing_up_counts_until_paid(db: MiniSupabase) -> None:
    db.tables.setdefault("tournament_entrants", [])
    ball = next(p for p in db.tables["players"] if p["nickname"] == "Ball")
    entry = {"id": str(uuid4()), "player_id": ball["id"], "share": 350, "pay_status": "unpaid", "pass_off": 0}
    db.tables["tournament_entrants"].append(dict(entry))
    lowered = ts.take_pass_off(db, entry)  # type: ignore[arg-type]
    assert (lowered["share"], lowered["pass_off"]) == (332, 18)
    assert ts.take_pass_off(db, lowered) is lowered  # type: ignore[arg-type]
    paid = {**entry, "pay_status": "slip_sent"}
    assert ts.take_pass_off(db, paid) is paid  # type: ignore[arg-type]
