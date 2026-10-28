"""Stock and pre-order rules for the club shop.

Supabase's REST API has no transactions, so taking stock is a
compare-and-swap: read the count, then UPDATE ... WHERE qty = <that count>.
If another order got there first the update matches no row and this reads
again. Two members buying the last shirt at the same moment cannot both
get it — one of them is told it has just sold out.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from supabase import Client

from app.db_utils import rows

CLUB_TZ = ZoneInfo("Asia/Bangkok")
ATTEMPTS = 5


def club_today() -> date:
    """The date at the club. A pre-order that closes on the 15th is open all
    of the 15th in Bangkok, not until 07:00 when UTC turns over."""
    return datetime.now(CLUB_TZ).date()


def stock_by_product(supabase: Client, product_ids: list[str]) -> dict[str, dict[str, int]]:
    if not product_ids:
        return {}
    result = supabase.table("product_stock").select("product_id, size, qty").in_("product_id", product_ids).execute()
    out: dict[str, dict[str, int]] = {}
    for row in rows(result):
        out.setdefault(str(row["product_id"]), {})[row["size"]] = int(row["qty"])
    return out


def ordered_by_product(supabase: Client, product_ids: list[str]) -> dict[str, dict[str, int]]:
    """Units ordered per product per size, not counting rejected orders."""
    if not product_ids:
        return {}
    result = (
        supabase.table("shop_orders")
        .select("product_id, size, qty, status")
        .in_("product_id", product_ids)
        .neq("status", "rejected")
        .execute()
    )
    out: dict[str, dict[str, int]] = {}
    for row in rows(result):
        if row.get("status") == "rejected":
            continue
        sizes = out.setdefault(str(row["product_id"]), {})
        sizes[row["size"]] = sizes.get(row["size"], 0) + int(row["qty"])
    return out


def is_open(product: dict[str, Any], stock: dict[str, int], today: date) -> bool:
    if not product.get("is_active"):
        return False
    if product["sale_type"] == "preorder":
        closes = product.get("preorder_closes_on")
        if closes is None:
            return False
        closes_on = closes if isinstance(closes, date) else date.fromisoformat(str(closes))
        return today <= closes_on
    return any(qty > 0 for qty in stock.values())


def take(supabase: Client, product_id: str, size: str, qty: int) -> bool:
    """Take `qty` of one size, or return False if there isn't that many."""
    for _ in range(ATTEMPTS):
        current = (
            supabase.table("product_stock")
            .select("qty")
            .eq("product_id", product_id)
            .eq("size", size)
            .limit(1)
            .execute()
        )
        found = rows(current)
        if not found:
            return False
        have = int(found[0]["qty"])
        if have < qty:
            return False
        swapped = (
            supabase.table("product_stock")
            .update({"qty": have - qty})
            .eq("product_id", product_id)
            .eq("size", size)
            .eq("qty", have)
            .execute()
        )
        if rows(swapped):
            return True
    return False


def give_back(supabase: Client, product_id: str, size: str, qty: int) -> None:
    """Return a refused order's units to the shelf. Best effort against a
    size the admin has since removed: then there is no shelf to return to."""
    for _ in range(ATTEMPTS):
        current = (
            supabase.table("product_stock")
            .select("qty")
            .eq("product_id", product_id)
            .eq("size", size)
            .limit(1)
            .execute()
        )
        found = rows(current)
        if not found:
            return
        have = int(found[0]["qty"])
        swapped = (
            supabase.table("product_stock")
            .update({"qty": have + qty})
            .eq("product_id", product_id)
            .eq("size", size)
            .eq("qty", have)
            .execute()
        )
        if rows(swapped):
            return


ALLOWED_MOVES: dict[str, set[str]] = {
    "pending": {"confirmed", "rejected"},
    "confirmed": {"delivered", "pending"},
    "delivered": {"confirmed"},
    "rejected": {"pending"},
}
"""Forward through the night, and one step back from each for a mis-tap.
A rejected order going back to pending takes its stock again."""


def hydrate(supabase: Client, product_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Product rows with their stock, ordered count and whether they can be
    ordered now — what both the shop and the admin screen draw."""
    ids = [str(p["id"]) for p in product_rows]
    stock = stock_by_product(supabase, ids)
    ordered = ordered_by_product(supabase, ids)
    today = club_today()
    out = []
    for p in product_rows:
        pid = str(p["id"])
        mine = stock.get(pid, {}) if p["sale_type"] == "stock" else {}
        out.append(
            {
                **p,
                "stock": mine,
                "ordered": sum(ordered.get(pid, {}).values()),
                "open": is_open(p, mine, today),
            }
        )
    return out
