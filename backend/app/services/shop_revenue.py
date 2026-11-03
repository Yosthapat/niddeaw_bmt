"""What the shop has made, for the dashboard, the shop page and the revenue
page.

Money in is an order an admin has confirmed or delivered: its slip was
checked, so the money is in the account. An order still pending is shown
apart ("waiting to check") and is not in any total, and a rejected one is
nothing at all.

What it cost is the expenses the club filed under the shop: the shop-cost
category and, as the club decided, shirts (jersey) too, since the shirts it
sells are the ones it has made. Those expenses already come off the
account's balance like every other one; the shop only uses them to say what
it made after costs.

An order counts on the day it was placed, in Bangkok — the day the slip
came in, which is the day the money did.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from supabase import Client

from app.db_utils import rows
from app.models.shop import ShopRevenue, ShopRevenueDay, ShopTopItem
from app.services.shop_service import CLUB_TZ

COUNTED = frozenset({"confirmed", "delivered"})
SHOP_COST_CATEGORIES = frozenset({"shop_cost", "jersey"})
TOP_ITEMS = 5
PAGE = 1000  # PostgREST's default row cap: anything longer is read in pages


def _all(supabase: Client, table: str, columns: str, **in_filter: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = supabase.table(table).select(columns)
        for column, values in in_filter.items():
            query = query.in_(column, values)
        page = rows(query.order("id").range(offset, offset + PAGE - 1).execute())
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def _club_date(stamp: str) -> date:
    return datetime.fromisoformat(stamp).astimezone(CLUB_TZ).date()


def summarise(
    orders: list[dict[str, Any]], items: list[dict[str, Any]], expenses: list[dict[str, Any]]
) -> ShopRevenue:
    counted = [o for o in orders if o.get("status") in COUNTED]
    pending = [o for o in orders if o.get("status") == "pending"]

    by_day: dict[date, list[float]] = defaultdict(lambda: [0.0, 0])
    for o in counted:
        day = by_day[_club_date(str(o["created_at"]))]
        day[0] += float(o["total"])
        day[1] += 1

    counted_ids = {str(o["id"]) for o in counted}
    by_item: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for line in items:
        if str(line.get("order_id")) in counted_ids:
            entry = by_item[str(line["product_name"])]
            entry[0] += int(line["qty"])
            entry[1] += float(line["line_total"])
    top = sorted(by_item.items(), key=lambda kv: (-kv[1][1], kv[0]))[:TOP_ITEMS]

    total = round(sum(float(o["total"]) for o in counted), 2)
    cost = round(sum(float(e["amount"]) for e in expenses if e.get("category") in SHOP_COST_CATEGORIES), 2)
    return ShopRevenue(
        total=total,
        orders=len(counted),
        pending_amount=round(sum(float(o["total"]) for o in pending), 2),
        pending_orders=len(pending),
        to_ship=sum(1 for o in counted if o.get("status") == "confirmed"),
        cost=cost,
        profit=round(total - cost, 2),
        daily=[
            ShopRevenueDay(date=d, amount=round(v[0], 2), orders=int(v[1]))
            for d, v in sorted(by_day.items(), reverse=True)
        ],
        top=[ShopTopItem(name=name, qty=int(v[0]), amount=round(v[1], 2)) for name, v in top],
    )


def load(supabase: Client) -> ShopRevenue:
    orders = _all(supabase, "shop_orders", "id, total, status, created_at", status=["pending", *sorted(COUNTED)])
    items = _all(supabase, "shop_order_items", "id, order_id, product_name, qty, line_total")
    expenses = _all(supabase, "expenses", "id, category, amount", category=sorted(SHOP_COST_CATEGORIES))
    return summarise(orders, items, expenses)
