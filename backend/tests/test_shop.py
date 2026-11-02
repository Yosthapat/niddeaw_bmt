"""The club shop, from a member's order to the admin's tally.

Two things here are about money and must not drift: the amount a member is
asked to pay comes from the product's price on the server, never from the
page; and stock is taken with a compare-and-swap, so two members buying the
last shirt cannot both get it.
"""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.deps import get_supabase
from app.main import app
from app.routers.public import shop as public_shop
from app.security import create_access_token
from app.services import shop_service
from tests.conftest import FakeResult, FakeStorage, FakeSupabase

PRODUCT_ID = str(uuid4())
PLAYER_ID = str(uuid4())
ORDER_ID = str(uuid4())
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
        "sizes": ["M", "XL"], "size_prices": {"XL": 420}, "preorder_closes_on": None, "preorder_delivers_on": None, "image_urls": [],
        "is_active": True, "sort_order": 0, "created_at": "2026-10-28T00:00:00Z",
    }
    return {**row, **overrides}


def order_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": ORDER_ID, "order_no": 12, "player_id": PLAYER_ID, "total": 780,
        "slip_url": "https://fake.supabase.co/storage/v1/object/public/shop/slip-a.jpg",
        "status": "pending", "note": None, "created_at": "2026-10-28T10:00:00Z",
        "updated_at": "2026-10-28T10:00:00Z",
    }
    return {**row, **overrides}


def item_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": str(uuid4()), "order_id": ORDER_ID, "product_id": PRODUCT_ID, "product_name": "เสื้อก๊วน สีดำ",
        "sale_type": "stock", "size": "M", "qty": 2, "unit_price": 390, "line_total": 780,
        "created_at": "2026-10-28T10:00:00Z",
    }
    return {**row, **overrides}


def slip() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (800, 1400), (240, 240, 240)).save(out, format="JPEG")
    return out.getvalue()


def cart(*lines: tuple[str, str, int]) -> list[dict[str, Any]]:
    return [{"product_id": pid, "size": size, "qty": qty} for pid, size, qty in lines] or [
        {"product_id": PRODUCT_ID, "size": "M", "qty": 2}
    ]


def order_form(*lines: tuple[str, str, int], **overrides: str) -> dict[str, str]:
    return {"player_id": PLAYER_ID, "items": json.dumps(cart(*lines)), **overrides}


class Shelf:
    """A Supabase stand-in that applies the filters the shop uses, so a
    test can stock M and XL differently and see which one an order took.
    The shared fake answers every query with the whole table, which can't
    say that."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables
        self.calls: list[tuple[str, Any, Any]] = []
        self.storage = FakeStorage()

    def table(self, name: str) -> ShelfQuery:
        return ShelfQuery(self, name)


class ShelfQuery:
    def __init__(self, db: Shelf, name: str) -> None:
        self.db, self.name = db, name
        self.op = "select"
        self.payload: Any = None
        self.filters: list[tuple[str, str, Any]] = []
        self.one = False

    def _call(self, name: str, *args: Any) -> ShelfQuery:
        self.db.calls.append((name, args, {"table": self.name}))
        return self

    def select(self, *_: Any, **__: Any) -> ShelfQuery:
        return self

    def insert(self, payload: Any) -> ShelfQuery:
        self.op, self.payload = "insert", payload
        return self._call("insert", payload)

    def update(self, payload: dict[str, Any]) -> ShelfQuery:
        self.op, self.payload = "update", payload
        return self._call("update", payload)

    def upsert(self, payload: Any, **_: Any) -> ShelfQuery:
        self.op, self.payload = "insert", payload
        return self._call("upsert", payload)

    def delete(self) -> ShelfQuery:
        self.op = "delete"
        return self._call("delete")

    def eq(self, column: str, value: Any) -> ShelfQuery:
        self.filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any) -> ShelfQuery:
        self.filters.append(("neq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> ShelfQuery:
        self.filters.append(("in", column, [str(v) for v in values]))
        return self

    def order(self, *_: Any, **__: Any) -> ShelfQuery:
        return self

    def limit(self, n: int) -> ShelfQuery:
        self.one = n == 1
        return self

    def _match(self, row: dict[str, Any]) -> bool:
        for kind, column, value in self.filters:
            have = row.get(column)
            if kind == "eq" and str(have) != str(value):
                return False
            if kind == "neq" and str(have) == str(value):
                return False
            if kind == "in" and str(have) not in value:
                return False
        return True

    def execute(self) -> Any:
        table = self.db.tables.setdefault(self.name, [])
        if self.op == "insert":
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            made = [{"id": str(uuid4()), "order_no": 13, "status": "pending", "note": None,
                     "created_at": "2026-10-28T11:00:00Z", "updated_at": "2026-10-28T11:00:00Z", **r} for r in new]
            table.extend(made)
            return FakeResult(made)
        found = [r for r in table if self._match(r)]
        if self.op == "update":
            for r in found:
                r.update(self.payload)
            return FakeResult(found)
        if self.op == "delete":
            self.db.tables[self.name] = [r for r in table if r not in found]
            return FakeResult(found)
        return FakeResult(found[:1] if self.one else found)


@pytest.fixture
def shelf(client: TestClient) -> Iterator[Shelf]:
    db = Shelf({})
    app.dependency_overrides[get_supabase] = lambda: db
    yield db
    app.dependency_overrides.pop(get_supabase, None)


def seed(db: Shelf | FakeSupabase, *, prod: dict[str, Any] | None = None, stock: int = 5, xl: int = 4) -> None:
    db.tables["products"] = [prod or product()]
    db.tables["product_stock"] = [
        {"product_id": PRODUCT_ID, "size": "M", "qty": stock},
        {"product_id": PRODUCT_ID, "size": "XL", "qty": xl},
    ]
    db.tables["players"] = [{"id": PLAYER_ID, "is_active": True, "nickname": "Pukpick", "member_seq": 25}]
    db.tables["shop_orders"] = [order_row()]
    db.tables["shop_order_items"] = [item_row()]
    db.tables["club_settings"] = [CLUB_SETTINGS]


def qty_of(db: Shelf, size: str) -> int:
    return next(int(r["qty"]) for r in db.tables["product_stock"] if r["size"] == size)


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


def test_each_size_costs_its_own_price(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    body = client.post("/api/shop/quote", json={"items": cart((PRODUCT_ID, "M", 1), (PRODUCT_ID, "XL", 2))}).json()
    assert [(line["size"], line["unit_price"], line["line_total"]) for line in body["lines"]] == [
        ("M", 390, 390), ("XL", 420, 840),
    ]
    assert body["total"] == 1230 and body["ok"] is True


def test_the_same_size_twice_is_one_line(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    body = client.post("/api/shop/quote", json={"items": cart((PRODUCT_ID, "M", 1), (PRODUCT_ID, "M", 2))}).json()
    assert [(line["size"], line["qty"]) for line in body["lines"]] == [("M", 3)]


def test_the_cart_says_which_line_cannot_be_had(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=1, xl=0)
    body = client.post(
        "/api/shop/quote", json={"items": cart((PRODUCT_ID, "M", 2), (PRODUCT_ID, "XL", 1), (PRODUCT_ID, "S", 1))}
    ).json()
    problems = {line["size"]: line["problem"] for line in body["lines"]}
    assert problems == {"M": "เหลือแค่ 1 ตัว", "XL": "หมดแล้ว", "S": "ไม่มีไซส์นี้แล้ว — เลือกใหม่"}
    assert body["ok"] is False


def test_the_amount_to_pay_comes_from_the_server_price(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    body = client.post("/api/shop/payment", json={"items": cart((PRODUCT_ID, "M", 1), (PRODUCT_ID, "XL", 1))}).json()
    assert body["amount"] == 810
    assert body["data_uri"].startswith("data:image/png;base64,")


def test_a_cart_is_one_order_priced_on_the_server_and_takes_its_stock(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    response = client.post(
        "/api/shop/orders",
        data={**order_form((PRODUCT_ID, "M", 2), (PRODUCT_ID, "XL", 1)), "total": "1"},  # the page cannot set a price
        files={"file": ("slip.jpg", slip(), "image/jpeg")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 1200
    assert [(i["size"], i["qty"], i["unit_price"]) for i in body["items"]] == [("M", 2, 390), ("XL", 1, 420)]
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL")) == (3, 3)
    path, data, options = shelf.storage.from_("shop").uploaded[0]
    assert path.startswith("slip-") and options["content-type"] == "image/jpeg"
    assert data[:2] == b"\xff\xd8"  # re-encoded, not whatever was uploaded
    assert "slip_url" not in body


def test_one_sold_out_line_refuses_the_whole_cart_and_takes_nothing(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=5, xl=0)
    response = client.post(
        "/api/shop/orders",
        data=order_form((PRODUCT_ID, "M", 2), (PRODUCT_ID, "XL", 1)),
        files={"file": ("slip.jpg", slip(), "image/jpeg")},
    )
    assert response.status_code == 409
    assert "XL" in response.json()["detail"] and "หมด" in response.json()["detail"]
    assert qty_of(shelf, "M") == 5
    assert not shelf.storage.from_("shop").uploaded


def test_stock_taken_for_one_line_goes_back_when_a_later_line_loses_a_race(shelf: Shelf) -> None:
    seed(shelf, stock=5, xl=1)
    lines = [
        {"product_id": PRODUCT_ID, "product_name": "เสื้อ", "sale_type": "stock", "size": "M", "qty": 2},
        {"product_id": PRODUCT_ID, "product_name": "เสื้อ", "sale_type": "stock", "size": "XL", "qty": 2},
    ]
    short = shop_service.take_lines(shelf, lines)  # type: ignore[arg-type]
    assert short is not None and short["size"] == "XL"
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL")) == (5, 1)


def test_a_cart_that_is_not_a_cart_is_refused(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    for items in ("[]", "not json", json.dumps([{"product_id": PRODUCT_ID, "qty": 11}])):
        response = client.post(
            "/api/shop/orders", data=order_form(items=items), files={"file": ("slip.jpg", slip(), "image/jpeg")}
        )
        assert response.status_code == 400, items


def test_a_closed_preorder_takes_no_more_orders(client: TestClient, shelf: Shelf) -> None:
    yesterday = (shop_service.club_today() - timedelta(days=1)).isoformat()
    seed(shelf, prod=product(sale_type="preorder", preorder_closes_on=yesterday))
    response = client.post("/api/shop/orders", data=order_form(), files={"file": ("slip.jpg", slip(), "image/jpeg")})
    assert response.status_code == 409
    assert "ปิดรับ" in response.json()["detail"]


def test_an_open_preorder_takes_no_stock(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, prod=product(sale_type="preorder", preorder_closes_on=shop_service.club_today().isoformat()))
    response = client.post("/api/shop/orders", data=order_form(), files={"file": ("slip.jpg", slip(), "image/jpeg")})
    assert response.status_code == 201
    assert qty_of(shelf, "M") == 5


def test_a_script_cannot_flood_the_shop_with_orders(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=1000)
    codes = [
        client.post(
            "/api/shop/orders", data=order_form((PRODUCT_ID, "M", 1)), files={"file": ("slip.jpg", slip(), "image/jpeg")}
        ).status_code
        for _ in range(public_shop.ORDERS_PER_WINDOW + 1)
    ]
    assert codes[-1] == 429 and set(codes[:-1]) == {201}


def test_a_member_sees_their_orders_with_items_and_without_the_slip(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    body = client.get(f"/api/shop/orders?player_id={PLAYER_ID}").json()
    assert body[0]["order_no"] == 12 and "slip_url" not in body[0]
    assert body[0]["items"][0]["size"] == "M"


def test_ordered_counts_skip_refused_orders(shelf: Shelf) -> None:
    seed(shelf)
    refused = str(uuid4())
    shelf.tables["shop_orders"].append(order_row(id=refused, status="rejected"))
    shelf.tables["shop_order_items"].append(item_row(order_id=refused, qty=5))
    assert shop_service.ordered_by_product(shelf, [PRODUCT_ID]) == {PRODUCT_ID: {"M": 2}}  # type: ignore[arg-type]


# ------------------------------------------------------------------- admin


@pytest.mark.parametrize(
    ("payload", "why"),
    [
        ({"name": "เสื้อ", "price": 390, "sale_type": "preorder", "sizes": ["M"]}, "วันปิดรับ"),
        ({"name": "เสื้อ", "price": 390, "sale_type": "stock", "sizes": ["M", "L"], "stock": {"M": 3}}, "ครบทุกไซส์"),
        ({"name": "เสื้อ", "price": 390, "sale_type": "stock", "sizes": ["M"]}, "ครบทุกไซส์"),
        (
            {"name": "เสื้อ", "price": 390, "sale_type": "stock", "sizes": ["M"], "stock": {"M": 1},
             "size_prices": {"XL": 420}},
            "เฉพาะไซส์ที่มีขาย",
        ),
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


def test_a_size_taken_off_takes_its_price_with_it(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    response = client.patch(
        f"/api/admin/shop/products/{PRODUCT_ID}", json={"sizes": ["M"], "stock": {"M": 5}}, headers=auth()
    )
    assert response.status_code == 200
    assert response.json()["size_prices"] == {}


def test_refusing_a_slip_puts_every_line_back(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=3, xl=1)
    shelf.tables["shop_order_items"].append(item_row(size="XL", qty=1, unit_price=420, line_total=420))
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}", json={"status": "rejected", "note": "ยอดไม่ตรง"}, headers=auth()
    )
    assert response.status_code == 200
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL")) == (5, 2)
    body = response.json()
    assert body["status"] == "rejected" and body["note"] == "ยอดไม่ตรง" and len(body["items"]) == 2


def test_an_order_cannot_come_back_if_a_line_has_sold_out(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=5, xl=0)
    shelf.tables["shop_orders"] = [order_row(status="rejected")]
    shelf.tables["shop_order_items"].append(item_row(size="XL", qty=1))
    response = client.patch(f"/api/admin/shop/orders/{ORDER_ID}", json={"status": "pending"}, headers=auth())
    assert response.status_code == 409
    assert qty_of(shelf, "M") == 5  # the M it took first went back


def test_a_delivered_order_cannot_jump_to_refused(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    shelf.tables["shop_orders"] = [order_row(status="delivered")]
    response = client.patch(f"/api/admin/shop/orders/{ORDER_ID}", json={"status": "rejected"}, headers=auth())
    assert response.status_code == 409


def test_a_product_with_orders_is_not_deleted(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    response = client.delete(f"/api/admin/shop/products/{PRODUCT_ID}", headers=auth())
    assert response.status_code == 409


def test_admin_orders_list_their_lines_and_who(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    body = client.get("/api/admin/shop/orders", headers=auth()).json()
    assert body[0]["player_code"] == "ND025" and body[0]["items"][0]["qty"] == 2


def test_only_an_admin_manages_the_shop(client: TestClient, supabase_rows: dict[str, Any]) -> None:
    assert client.get("/api/admin/shop/orders").status_code == 401


# ------------------------------------------------------- fixing an order line


def _line(shelf: Shelf) -> dict[str, Any]:
    return next(i for i in shelf.tables["shop_order_items"] if i["order_id"] == ORDER_ID)


def test_fixing_the_size_reprices_the_line_and_moves_the_stock(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=5, xl=4)
    line = _line(shelf)
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}", json={"size": "XL"}, headers=auth()
    )
    assert response.status_code == 200
    assert (line["size"], line["unit_price"], line["line_total"]) == ("XL", 420, 840)
    assert response.json()["total"] == 840  # was 780: the admin collects 60 more
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL")) == (7, 2)


def test_fixing_how_many_takes_or_returns_only_the_difference(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=5)
    line = _line(shelf)
    url = f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}"
    assert client.patch(url, json={"qty": 3}, headers=auth()).json()["total"] == 1170
    assert qty_of(shelf, "M") == 4
    assert client.patch(url, json={"qty": 1}, headers=auth()).json()["total"] == 390
    assert qty_of(shelf, "M") == 6


def test_a_size_that_has_run_out_is_refused_and_nothing_moves(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, stock=5, xl=1)
    line = _line(shelf)
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}", json={"size": "XL"}, headers=auth()
    )
    assert response.status_code == 409 and "XL" in response.json()["detail"]
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL"), line["size"]) == (5, 1, "M")


def test_a_handed_over_order_is_not_edited(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    shelf.tables["shop_orders"] = [order_row(status="delivered")]
    line = _line(shelf)
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}", json={"size": "XL"}, headers=auth()
    )
    assert response.status_code == 409


def test_a_size_already_on_the_order_is_not_doubled(client: TestClient, shelf: Shelf) -> None:
    seed(shelf)
    shelf.tables["shop_order_items"].append(item_row(size="XL", qty=1, unit_price=420, line_total=420))
    line = _line(shelf)
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}", json={"size": "XL"}, headers=auth()
    )
    assert response.status_code == 409 and "XL" in response.json()["detail"]


def test_fixing_a_preorder_line_touches_no_stock(client: TestClient, shelf: Shelf) -> None:
    seed(shelf, prod=product(sale_type="preorder", preorder_closes_on="2026-12-01"))
    line = _line(shelf)
    line["sale_type"] = "preorder"
    response = client.patch(
        f"/api/admin/shop/orders/{ORDER_ID}/items/{line['id']}", json={"size": "XL"}, headers=auth()
    )
    assert response.status_code == 200 and response.json()["total"] == 840
    assert (qty_of(shelf, "M"), qty_of(shelf, "XL")) == (5, 4)
