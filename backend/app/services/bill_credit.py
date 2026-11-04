"""Paying a night's bill with club credit, and giving it back.

billings.credit_used is how much of the bill credit has paid (whole
credits; 1 credit = 1 baht). The member taps once in LINE: credit pays as
much of what's left as it can. Enough credit → the bill is paid there and
then. Not enough → all of it goes on the bill and the QR asks for the rest
by transfer, which the admin checks like any slip.

Money: the baht behind that credit was counted when the top-up came in,
so the dues money counted for a bill is its amount less credit_used.

Both writes are compare-and-swaps — the balance (credit_service.apply) and
the bill (UPDATE ... WHERE credit_used = what was read) — so a double tap
or the admin marking it paid at the same moment can't spend credit twice:
if the bill moved under us, the credit just taken is put back.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.services import billing_service, credit_service

EPS = 1e-9


def amount(row: dict[str, Any]) -> float:
    return float(billing_service.effective_amount(row["amount_calc"], row.get("amount_adjusted")))


def used(row: dict[str, Any]) -> int:
    return int(row.get("credit_used") or 0)


def left_to_pay(row: dict[str, Any]) -> float:
    """What is still owed in baht, after the credit put on the bill."""
    return max(0.0, round(amount(row) - used(row), 2))


def _claim(supabase: Client, row: dict[str, Any], fields: dict[str, Any], *, unpaid: bool) -> list[dict[str, Any]]:
    q = (
        supabase.table("billings")
        .update({**fields, "updated_at": datetime.now(UTC).isoformat()})
        .eq("id", str(row["id"]))
        .eq("credit_used", used(row))
    )
    if unpaid:
        q = q.eq("paid_status", "unpaid")
    return rows(q.execute())


def pay(supabase: Client, row: dict[str, Any], note: str) -> dict[str, Any]:
    """Put the member's credit on their bill: as much of what's left as
    their balance covers. Returns the bill after."""
    if row["paid_status"] == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้จ่ายแล้ว")
    if row.get("slip_url"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ส่งสลิปบิลนี้ไปแล้ว รอแอดมินตรวจ"
        )
    owed = left_to_pay(row)
    if owed <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้ไม่มียอดค้าง")
    player_id = str(row["player_id"])
    # Whole credits only: a bill with satang leaves those satang to transfer.
    take = min(credit_service.balance(supabase, player_id), math.floor(owed + EPS))
    if take <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ไม่มีเครดิตให้ใช้")
    try:
        credit_service.apply(supabase, player_id, -take, "bill", ref_id=row["id"], note=note)
    except credit_service.NotEnoughCredit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="เครดิตเปลี่ยนไปแล้ว — ลองใหม่อีกครั้ง"
        ) from None
    after = used(row) + take
    covered = after + EPS >= amount(row)
    claimed = _claim(
        supabase, row, {"credit_used": after, "paid_status": "paid" if covered else "unpaid"}, unpaid=True
    )
    if not claimed:
        credit_service.apply(supabase, player_id, take, "refund", ref_id=row["id"], note=f"คืนเครดิต · {note}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้เปลี่ยนไปแล้ว — รีเฟรชแล้วลองใหม่")
    return claimed[0]


def give_back(
    supabase: Client,
    row: dict[str, Any],
    credits: int,
    note: str,
    *,
    admin_id: UUID | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Take `credits` off the bill's credit_used and put them back on the
    member's balance. `extra` are other bill fields to set in the same
    write (paid_status when the admin undoes a payment)."""
    credits = min(credits, used(row))
    if credits <= 0 and not extra:
        return row
    claimed = _claim(supabase, row, {"credit_used": used(row) - credits, **(extra or {})}, unpaid=False)
    if not claimed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้เปลี่ยนไปแล้ว — รีเฟรชแล้วลองใหม่")
    if credits > 0:
        credit_service.apply(
            supabase, str(row["player_id"]), credits, "refund", ref_id=row["id"], note=note, admin_id=admin_id
        )
    return claimed[0]


def fit(supabase: Client, row: dict[str, Any], *, admin_id: UUID | str | None = None) -> dict[str, Any]:
    """After a bill's amount changed (the admin adjusted it, or it was
    billed again): credit beyond the new amount goes back to the member,
    and a bill credit now fully covers is paid."""
    if used(row) == 0:
        return row
    over = math.ceil(used(row) - amount(row) - EPS)
    if over > 0:
        row = give_back(supabase, row, over, "คืนเครดิต · ยอดบิลลดลง", admin_id=admin_id)
    if row["paid_status"] == "unpaid" and used(row) > 0 and used(row) + EPS >= amount(row) and not row.get("slip_url"):
        claimed = _claim(supabase, row, {"paid_status": "paid"}, unpaid=True)
        row = claimed[0] if claimed else row
    return row


def mark_unpaid(supabase: Client, row: dict[str, Any], admin_id: UUID | str) -> dict[str, Any]:
    """The admin undoes a payment: any credit on the bill goes back too,
    so 'unpaid' means nothing of it is paid."""
    return give_back(
        supabase, row, used(row), "คืนเครดิต · แอดมินยกเลิกการจ่ายบิล", admin_id=admin_id, extra={"paid_status": "unpaid"}
    )
