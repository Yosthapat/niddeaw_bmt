"""What the shop has made: only checked orders count, pending ones wait
apart, and the shop's costs (shop_cost and shirts) come off for its profit."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token
from app.services.shop_revenue import summarise
from tests.conftest import FakeSupabase


def order(status: str, total: float, at: str = "2026-10-31T12:00:00Z") -> dict[str, Any]:
    return {"id": str(uuid4()), "status": status, "total": total, "created_at": at}


def line(o: dict[str, Any], name: str, qty: int, amount: float) -> dict[str, Any]:
    return {"id": str(uuid4()), "order_id": o["id"], "product_name": name, "qty": qty, "line_total": amount}


def test_only_confirmed_and_delivered_orders_are_money_in() -> None:
    orders = [order("confirmed", 900), order("delivered", 200), order("pending", 450), order("rejected", 390)]
    out = summarise(orders, [], [])
    assert out.total == 1100
    assert out.orders == 2
    assert (out.pending_orders, out.pending_amount) == (1, 450)
    assert out.to_ship == 1  # confirmed, not yet delivered


def test_an_order_counts_on_its_bangkok_day() -> None:
    # 18:30 UTC on the 31st is 01:30 on 1 Nov in Bangkok.
    late = order("confirmed", 300, "2026-10-31T18:30:00Z")
    early = order("confirmed", 100, "2026-10-31T10:00:00+00:00")
    out = summarise([late, early], [], [])
    assert [(d.date, d.amount, d.orders) for d in out.daily] == [
        (date(2026, 11, 1), 300, 1),
        (date(2026, 10, 31), 100, 1),
    ]


def test_top_items_come_from_counted_orders_only() -> None:
    ok, waiting = order("confirmed", 1100), order("pending", 5000)
    items = [
        line(ok, "เสื้อก๊วน", 2, 900),
        line(ok, "สติกเกอร์", 4, 200),
        line(waiting, "พวงกุญแจ", 10, 5000),
    ]
    out = summarise([ok, waiting], items, [])
    assert [(t.name, t.qty, t.amount) for t in out.top] == [("เสื้อก๊วน", 2, 900), ("สติกเกอร์", 4, 200)]


def test_shop_cost_and_shirts_come_off_for_profit() -> None:
    expenses = [
        {"id": "1", "category": "shop_cost", "amount": 1500},
        {"id": "2", "category": "jersey", "amount": 4000},
        {"id": "3", "category": "court_fee", "amount": 1200},
    ]
    out = summarise([order("delivered", 9000)], [], expenses)
    assert out.cost == 5500
    assert out.profit == 3500


def test_nothing_sold_is_all_zeros() -> None:
    out = summarise([], [], [])
    assert (out.total, out.orders, out.pending_orders, out.cost, out.profit) == (0, 0, 0, 0, 0)
    assert out.daily == [] and out.top == []


@pytest.fixture
def client() -> Iterator[tuple[TestClient, FakeSupabase]]:
    paid = order("confirmed", 780)
    db = FakeSupabase(
        {
            "shop_orders": [paid, order("pending", 390)],
            "shop_order_items": [line(paid, "เสื้อก๊วน", 2, 780)],
            "expenses": [{"id": "e", "category": "shop_cost", "amount": 300}],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: db
    yield TestClient(app), db
    app.dependency_overrides.pop(get_supabase, None)


def test_the_endpoint_needs_an_admin(client: tuple[TestClient, FakeSupabase]) -> None:
    c, _ = client
    assert c.get("/api/admin/shop/revenue").status_code == 401


def test_the_endpoint_sums_the_shop(client: tuple[TestClient, FakeSupabase]) -> None:
    c, db = client
    token = create_access_token(admin_id=str(uuid4()), role="admin")
    res = c.get("/api/admin/shop/revenue", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert (body["total"], body["pending_amount"], body["cost"], body["profit"]) == (780, 390, 300, 480)
    assert body["top"] == [{"name": "เสื้อก๊วน", "qty": 2, "amount": 780}]
    # Asked only for the statuses and categories it counts.
    asked = [(args[0], sorted(args[1])) for name, args, _ in db.calls if name == "in_"]
    assert ("status", ["confirmed", "delivered", "pending"]) in asked
    assert ("category", ["jersey", "shop_cost"]) in asked
