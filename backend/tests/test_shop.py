"""The club shop, from a member's order to the admin's tally.

Two things here are about money and must not drift: the amount a member is
asked to pay comes from the product's price on the server, never from the
page; and stock is taken with a compare-and-swap, so two members buying the
last shirt cannot both get it.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.routers.public import shop as public_shop
from app.security import create_access_token
from app.services import shop_service
from tests.conftest import FakeSupabase

PRODUCT_ID = str(uuid4())
PLAYER_ID = str(uuid4())
CLUB_SETTINGS = {
    "id": 1, "payment_method": "promptpay", "promptpay_id": "0812345678", "promptpay_type": "phone",
    "bank_name": None, "bank_account_number": None, "bank_account_name": None, "uploaded_qr_url": None,
    "default_court_fee_per_person": 80, "default_shuttlecock_price_per_game": 29,
}


@pytest.fixture(autouse=True)
def _fresh_throttle() -> None:
    public_shop.reset_throttle()


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def product(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": PRODUCT_ID, "name": "เสื้อก๊วน สีดำ", "description": None, "price": 390, "sale_type": "stock",
        "sizes": ["M", "L"], "preorder_closes_on": None, "preorder_delivers_on": None, "image_urls": [],
        "is_active": True, "sort_order": 0, "created_at": "2026-10-28T00:00:00Z",
    }
    return {**row, **overrides}


def order_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": str(uuid4()), "order_no": 12, "player_id": PLAYER_ID, "product_id": PRODUCT_ID,
        "product_name": "เสื้อก๊วน สีดำ", "sale_type": "stock", "size": "M", "qty": 2, "unit_price": 390,
        "total": 780, "slip_url": "https://fake.supabase.co/storage/v1/object/public/shop/slip-a.jpg",
        "status": "pending", "note": None, "created_at": "2026-10-28T10:00:00Z",
        "updated_at": "2026-10-28T10:00:00Z",
    }
    return {**row, **overrides}


def slip() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (800, 1400), (240, 240, 240)).save(out, format="JPEG")
    return out.getvalue()


def order_form(**overrides: Any) -> dict[str, str]:
    form = {"product_id": PRODUCT_ID, "player_id": PLAYER_ID, "qty": "2", "size": "M"}
    return {**form, **overrides}


def seed(spy: FakeSupabase, *, prod: dict[str, Any] | None = None, stock: int = 5) -> None:
    spy.tables["products"] = [prod or product()]
    spy.tables["product_stock"] = [{"product_id": PRODUCT_ID, "size": "M", "qty": stock}]
    spy.tables["players"] = [{"id": PLAYER_ID, "is_active": True, "nickname": "Pukpick", "member_seq": 25}]
    spy.tables["shop_orders"] = [order_row()]
    spy.tables["club_settings"] = [CLUB_SETTINGS]


# --------------------------------------------------------------- the rules


class Racing:
    """A stock table where someone else buys one between our read and our
    write, once — the case the compare-and-swap exists for."""

    def __init__(self, qty: int) -> None:
        self.qty = qty
        self.raced = False
        self.writes: list[int] = []

    def table(self, name: str) -> Racing:
        self._op: str | None = None
        self._filters: dict[str, Any] = {}
        return self

    def select(self, *_: Any) -> Racing:
        self._op = "select"
        return self

    def update(self, values: dict[str, Any]) -> Racing:
        self._op, self._values = "update", values
        return self

    def eq(self, column: str, value: Any) -> Racing:
        self._filters[column] = value
        return self

    def limit(self, _: int) -> Racing:
        return self

    def execute(self) -> Any:
        class Result:
            def __init__(self, data: list[dict[str, Any]]) -> None:
                self.data = data

        if self._op == "select":
            seen = self.qty
            if not self.raced:  # someone else takes one right after we look
                self.raced = True
                self.qty -= 1
            return Result([{"qty": seen}])
        if self._filters.get("qty") != self.qty:
            return Result([])
        self.qty = self._values["qty"]
        self.writes.append(self.qty)
        return Result([{"qty": self.qty}])


def test_taking_stock_retries_when_someone_else_got_there_first() -> None:
    table = Racing(qty=3)
    assert shop_service.take(table, PRODUCT_ID, "M", 1) is True  # type: ignore[arg-type]
    assert table.qty == 1  # 3, minus theirs, minus ours — not 2
    assert table.writes == [1]


def test_the_last_one_cannot_be_sold_twice() -> None:
    table = Racing(qty=1)
    assert shop_service.take(table, PRODUCT_ID, "M", 1) is False  # type: ignore[arg-type]
    assert table.qty == 0


def test_a_preorder_is_open_all_of_its_closing_day() -> None:
    today = date(2026, 11, 15)
    row = product(sale_type="preorder", preorder_closes_on="2026-11-15")
    assert shop_service.is_open(row, {}, today)
    assert not shop_service.is_open(row, {}, today + timedelta(days=1))


def test_a_stock_product_with_nothing_left_is_not_open() -> None:
    assert not shop_service.is_open(product(), {"M": 0, "L": 0}, date(2026, 11, 1))
    assert shop_service.is_open(product(), {"M": 0, "L": 1}, date(2026, 11, 1))


# --------------------------------------------------------------- ordering


def test_the_amount_to_pay_comes_from_the_server_price(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy)
    body = client.get(f"/api/shop/products/{PRODUCT_ID}/payment?qty=2").json()
    assert body["amount"] == 780
    assert body["data_uri"].startswith("data:image/png;base64,")


def test_an_order_is_priced_on_the_server_and_takes_its_stock(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    seed(supabase_spy)
    response = client.post(
        "/api/shop/orders",
        data={**order_form(), "total": "1", "unit_price": "1"},  # the page cannot set a price
        files={"file": ("slip.jpg", slip(), "image/jpeg")},
    )
    assert response.status_code == 201
    inserted = next(args[0] for name, args, _ in supabase_spy.calls if name == "insert")
    assert (inserted["unit_price"], inserted["total"]) == (390, 780)
    stock_writes = [args[0] for name, args, _ in supabase_spy.calls if name == "update"]
    assert {"qty": 3} in stock_writes
    path, data, options = supabase_spy.storage.from_("shop").uploaded[0]
    assert path.startswith("slip-") and options["content-type"] == "image/jpeg"
    assert data[:2] == b"\xff\xd8"  # re-encoded, not whatever was uploaded
    assert "slip_url" not in response.json()


def test_a_sold_out_size_is_refused_and_nothing_is_stored(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    seed(supabase_spy, stock=1)
    response = client.post(
        "/api/shop/orders", data=order_form(qty="2"), files={"file": ("slip.jpg", slip(), "image/jpeg")}
    )
    assert response.status_code == 409
    assert "หมด" in response.json()["detail"]
    assert not supabase_spy.storage.from_("shop").uploaded


def test_a_size_the_product_does_not_have_is_refused(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy)
    response = client.post(
        "/api/shop/orders", data=order_form(size="XXXL"), files={"file": ("slip.jpg", slip(), "image/jpeg")}
    )
    assert response.status_code == 400


def test_a_closed_preorder_takes_no_more_orders(client: TestClient, supabase_spy: FakeSupabase) -> None:
    yesterday = (shop_service.club_today() - timedelta(days=1)).isoformat()
    seed(supabase_spy, prod=product(sale_type="preorder", preorder_closes_on=yesterday))
    response = client.post(
        "/api/shop/orders", data=order_form(), files={"file": ("slip.jpg", slip(), "image/jpeg")}
    )
    assert response.status_code == 409
    assert "ปิดรับ" in response.json()["detail"]


def test_an_open_preorder_takes_no_stock(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy, prod=product(sale_type="preorder", preorder_closes_on=shop_service.club_today().isoformat()))
    response = client.post(
        "/api/shop/orders", data=order_form(), files={"file": ("slip.jpg", slip(), "image/jpeg")}
    )
    assert response.status_code == 201
    assert not [c for c in supabase_spy.calls if c[0] == "update"]


def test_a_script_cannot_flood_the_shop_with_orders(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy, stock=1000)
    codes = [
        client.post(
            "/api/shop/orders", data=order_form(qty="1"), files={"file": ("slip.jpg", slip(), "image/jpeg")}
        ).status_code
        for _ in range(public_shop.ORDERS_PER_WINDOW + 1)
    ]
    assert codes[-1] == 429 and set(codes[:-1]) == {201}


def test_a_member_sees_their_orders_without_the_slip(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy)
    body = client.get(f"/api/shop/orders?player_id={PLAYER_ID}").json()
    assert body[0]["order_no"] == 12 and "slip_url" not in body[0]


# ------------------------------------------------------------------- admin


@pytest.mark.parametrize(
    ("payload", "why"),
    [
        ({"name": "เสื้อ", "price": 390, "sale_type": "preorder", "sizes": ["M"]}, "วันปิดรับ"),
        ({"name": "เสื้อ", "price": 390, "sale_type": "stock", "sizes": ["M", "L"], "stock": {"M": 3}}, "ครบทุกไซซ์"),
        ({"name": "เสื้อ", "price": 390, "sale_type": "stock", "sizes": ["M"]}, "ครบทุกไซซ์"),
    ],
)
def test_a_product_must_be_sellable_as_described(
    client: TestClient, supabase_spy: FakeSupabase, payload: dict[str, Any], why: str
) -> None:
    response = client.post("/api/admin/shop/products", json=payload, headers=auth())
    assert response.status_code == 400 and why in response.json()["detail"]


def test_a_size_listed_twice_is_refused(client: TestClient, supabase_spy: FakeSupabase) -> None:
    payload = {"name": "เสื้อ", "price": 390, "sale_type": "preorder", "sizes": ["M", "m"], "preorder_closes_on": "2026-12-01"}
    assert client.post("/api/admin/shop/products", json=payload, headers=auth()).status_code == 422


def test_refusing_a_slip_puts_the_stock_back(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy, stock=3)
    order = order_row()
    supabase_spy.tables["shop_orders"] = [order]
    response = client.patch(
        f"/api/admin/shop/orders/{order['id']}", json={"status": "rejected", "note": "ยอดไม่ตรง"}, headers=auth()
    )
    assert response.status_code == 200
    updates = [args[0] for name, args, _ in supabase_spy.calls if name == "update"]
    assert {"qty": 5} in updates  # 3 on the shelf + the order's 2
    assert any(u.get("status") == "rejected" and u.get("note") == "ยอดไม่ตรง" for u in updates)


def test_a_delivered_order_cannot_jump_to_refused(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy)
    order = order_row(status="delivered")
    supabase_spy.tables["shop_orders"] = [order]
    response = client.patch(f"/api/admin/shop/orders/{order['id']}", json={"status": "rejected"}, headers=auth())
    assert response.status_code == 409


def test_a_product_with_orders_is_not_deleted(client: TestClient, supabase_spy: FakeSupabase) -> None:
    seed(supabase_spy)
    response = client.delete(f"/api/admin/shop/products/{PRODUCT_ID}", headers=auth())
    assert response.status_code == 409


def test_only_an_admin_manages_the_shop(client: TestClient, supabase_rows: dict[str, Any]) -> None:
    assert client.get("/api/admin/shop/orders").status_code == 401
