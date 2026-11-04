"""Club credit: balances, the ledger, and top-ups.

A member's balance lives in player_credits and is only ever changed by
apply(): a compare-and-swap on the balance (UPDATE ... WHERE balance = what
was read), retried if someone else changed it first, then a ledger row
saying what it was for and what the balance became. Supabase's REST API
has no transactions, so this is the same pattern shop stock uses
(shop_service.take): the database refuses a negative balance outright,
and two spends at the same moment can't both use the same credit.

Money: a top-up's price is baht received (ledger.cash), counted as money in
when it is approved. Spending credit later moves no money, so whatever it
pays for must not be counted as money in a second time.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.models.credit import CreditDay, CreditSummary, LedgerEntry
from app.services.shop_service import CLUB_TZ

ATTEMPTS = 6
PAGE = 1000


class NotEnoughCredit(Exception):
    """The balance would go below zero."""


def balance(supabase: Client, player_id: UUID | str) -> int:
    found = rows(
        supabase.table("player_credits").select("balance").eq("player_id", str(player_id)).limit(1).execute()
    )
    return int(found[0]["balance"]) if found else 0


def _swap(supabase: Client, player_id: str, delta: int) -> int:
    """Move the balance by delta; returns the balance after. Raises
    NotEnoughCredit rather than going below zero."""
    for _ in range(ATTEMPTS):
        found = rows(
            supabase.table("player_credits").select("balance").eq("player_id", player_id).limit(1).execute()
        )
        if not found:
            if delta < 0:
                raise NotEnoughCredit
            try:
                supabase.table("player_credits").insert(
                    {"player_id": player_id, "balance": delta, "updated_at": datetime.now(UTC).isoformat()}
                ).execute()
                return delta
            except Exception:  # noqa: BLE001, S112 — someone created the row first; go round again
                continue
        before = int(found[0]["balance"])
        after = before + delta
        if after < 0:
            raise NotEnoughCredit
        swapped = rows(
            supabase.table("player_credits")
            .update({"balance": after, "updated_at": datetime.now(UTC).isoformat()})
            .eq("player_id", player_id)
            .eq("balance", before)
            .execute()
        )
        if swapped:
            return after
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="เครดิตเปลี่ยนพร้อมกันหลายรายการ — ลองใหม่อีกครั้ง")


def apply(
    supabase: Client,
    player_id: UUID | str,
    delta: int,
    kind: str,
    *,
    cash: float | None = None,
    ref_id: UUID | str | None = None,
    note: str | None = None,
    admin_id: UUID | str | None = None,
) -> int:
    """Change a balance and write why. Returns the balance after."""
    pid = str(player_id)
    after = _swap(supabase, pid, delta)
    supabase.table("credit_ledger").insert(
        {
            "player_id": pid,
            "delta": delta,
            "balance_after": after,
            "kind": kind,
            "cash": cash,
            "ref_id": str(ref_id) if ref_id else None,
            "note": note,
            "admin_id": str(admin_id) if admin_id else None,
        }
    ).execute()
    return after


def history(supabase: Client, player_id: UUID | str, limit: int = 40) -> list[LedgerEntry]:
    found = rows(
        supabase.table("credit_ledger")
        .select("*")
        .eq("player_id", str(player_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    found = [r for r in found if str(r["player_id"]) == str(player_id)]
    found.sort(key=lambda r: str(r["created_at"]), reverse=True)
    return [LedgerEntry.model_validate(r) for r in found[:limit]]


def approve_topup(supabase: Client, topup_id: UUID, admin_id: UUID | str) -> dict[str, Any]:
    """Credit a top-up whose slip the admin checked. Approving twice (two
    admins, a double tap) credits once: the top-up is claimed first."""
    found = rows(supabase.table("credit_topups").select("*").eq("id", str(topup_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการเติมเครดิตนี้")
    topup = found[0]
    if topup["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="รายการนี้ตรวจไปแล้ว — รีเฟรชหน้า")
    if not topup.get("slip_url"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ยังไม่ได้แนบสลิป")
    claimed = rows(
        supabase.table("credit_topups")
        .update({"status": "approved", "decided_at": datetime.now(UTC).isoformat(), "note": None})
        .eq("id", str(topup_id))
        .eq("status", "pending")
        .execute()
    )
    if not claimed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="รายการนี้ตรวจไปแล้ว — รีเฟรชหน้า")
    apply(
        supabase,
        topup["player_id"],
        int(topup["credits"]),
        "topup",
        cash=float(topup["price"]),
        ref_id=topup_id,
        note=f"เติมเครดิต · จ่าย ฿{float(topup['price']):,.0f}",
        admin_id=admin_id,
    )
    return claimed[0]


def all_rows(supabase: Client, table: str, columns: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = rows(supabase.table(table).select(columns).order("id").range(offset, offset + PAGE - 1).execute())
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def _club_date(stamp: str) -> str:
    return datetime.fromisoformat(stamp).astimezone(CLUB_TZ).date().isoformat()


def summary(supabase: Client) -> CreditSummary:
    """Cash that came in for credit (and went back out), by Bangkok day,
    and the credit members still hold."""
    ledger = [r for r in all_rows(supabase, "credit_ledger", "id, delta, cash, created_at") if r.get("cash") is not None]
    by_day: dict[str, float] = defaultdict(float)
    cash_in = cash_out = 0.0
    for r in ledger:
        cash = float(r["cash"])
        signed = cash if int(r["delta"]) > 0 else -cash
        if signed >= 0:
            cash_in += cash
        else:
            cash_out += cash
        by_day[_club_date(str(r["created_at"]))] += signed
    balances = all_rows(supabase, "player_credits", "player_id, balance")
    pending = [t for t in all_rows(supabase, "credit_topups", "id, status, slip_url") if t["status"] == "pending" and t.get("slip_url")]
    return CreditSummary(
        cash_in=round(cash_in, 2),
        cash_out=round(cash_out, 2),
        outstanding=sum(int(b["balance"]) for b in balances),
        pending_topups=len(pending),
        daily=[CreditDay(date=d, cash=round(v, 2)) for d, v in sorted(by_day.items(), reverse=True)],
    )
