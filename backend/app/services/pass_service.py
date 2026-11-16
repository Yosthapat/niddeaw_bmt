"""Niddeaw Pass: a monthly pass bought with credit (0045_niddeaw_pass.sql).

A pass runs PASS_DAYS from when it is bought; buying again while one runs
adds the days on the end, so nothing is lost by renewing early. Only a
member holding a credit card (a 1,000 pack or more bought through LINE,
credit not yet spent: credit_card_service) can buy one.

While it runs, its holder:
- goes onto the side with the better odds, PASS_EDGE or more, when the
  suggestion can manage it (matchmaking_service);
- may name up to BLOCKS_PER_NIGHT members a night not to be partnered with.
  They can still meet across the net, and nobody else sees the list.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.services import credit_card_service, credit_service, line_checkin

PASS_DAYS = 30
DEFAULT_PRICE = 249
BLOCKS_PER_NIGHT = 2
PASS_EDGE = 0.50


def _iso(when: datetime) -> str:
    return when.astimezone(UTC).isoformat()


def _when(value: Any) -> datetime:
    text = str(value).replace("Z", "+00:00")
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def price(supabase: Client) -> int:
    found = rows(supabase.table("club_settings").select("*").limit(1).execute())
    value = found[0].get("pass_price") if found else None
    return int(value) if value else DEFAULT_PRICE


def passes_of(supabase: Client, player_id: UUID | str) -> list[dict[str, Any]]:
    found = rows(supabase.table("passes").select("*").eq("player_id", str(player_id)).execute())
    return [p for p in found if str(p["player_id"]) == str(player_id)]


def runs_until(supabase: Client, player_id: UUID | str, at: datetime | None = None) -> datetime | None:
    """When their pass ends, if one runs at `at` (now by default). Passes
    bought back to back run on from each other."""
    moment = at or datetime.now(UTC)
    spans = [(_when(p["starts_at"]), _when(p["ends_at"])) for p in passes_of(supabase, player_id)]
    covering = [end for start, end in spans if start <= moment < end]
    if not covering:
        return None
    last = max(covering)
    moved = True
    while moved:
        moved = False
        for start, end in spans:
            if start <= last < end:
                last, moved = end, True
    return last


def holders(supabase: Client, at: datetime | None = None) -> set[str]:
    """Everyone with a pass running at `at` (now by default)."""
    moment = at or datetime.now(UTC)
    return {
        str(p["player_id"])
        for p in rows(supabase.table("passes").select("player_id,starts_at,ends_at").execute())
        if _when(p["starts_at"]) <= moment < _when(p["ends_at"])
    }


def eligible(supabase: Client, player_id: UUID | str) -> bool:
    return str(player_id) in credit_card_service.all_cards(supabase)


def buy(supabase: Client, player_id: UUID | str) -> datetime:
    """Take the price off their credit and start (or extend) their pass.
    Returns when it now ends."""
    pid = str(player_id)
    if not eligible(supabase, pid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ซื้อ Pass ได้เฉพาะคนที่มีบัตรเครดิต (เติมแพ็ก 1,000 ขึ้นไป) — เติมเครดิตก่อนนะ",
        )
    cost = price(supabase)
    now = datetime.now(UTC)
    start = runs_until(supabase, pid, now) or now
    end = start + timedelta(days=PASS_DAYS)
    try:
        credit_service.apply(supabase, pid, -cost, "pass", note=f"Niddeaw Pass {PASS_DAYS} วัน")
    except credit_service.NotEnoughCredit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"เครดิตไม่พอ — Pass ใช้ {cost} เครดิต"
        ) from None
    try:
        supabase.table("passes").insert(
            {"player_id": pid, "starts_at": _iso(start), "ends_at": _iso(end), "credits": cost}
        ).execute()
    except Exception:
        # the credit went but the pass didn't: give it back before saying so
        credit_service.apply(supabase, pid, cost, "refund", note="Niddeaw Pass ไม่สำเร็จ — คืนเครดิต")
        raise
    return end


# ---------------------------------------------------------------- tonight


def night_of(supabase: Client, player_id: UUID | str) -> dict[str, Any] | None:
    """The open night they are checked in to (and not out of), if any."""
    nights = [n for n in rows(supabase.table("sessions").select("*").eq("status", "open").execute()) if line_checkin.is_current(n)]
    for night in sorted(nights, key=lambda n: str(n["date"]), reverse=True):
        found = rows(
            supabase.table("checkins")
            .select("*")
            .eq("session_id", str(night["id"]))
            .eq("player_id", str(player_id))
            .limit(1)
            .execute()
        )
        if found and found[0].get("checkout_time") is None:
            return night
    return None


def checked_in(supabase: Client, session_id: UUID | str) -> list[str]:
    return [
        str(c["player_id"])
        for c in rows(supabase.table("checkins").select("*").eq("session_id", str(session_id)).execute())
        if c.get("checkout_time") is None and str(c["session_id"]) == str(session_id)
    ]


def blocks_of(supabase: Client, session_id: UUID | str, player_id: UUID | str) -> list[str]:
    return [
        str(b["blocked_id"])
        for b in rows(
            supabase.table("pass_blocks").select("*").eq("session_id", str(session_id)).eq("player_id", str(player_id)).execute()
        )
        if str(b["session_id"]) == str(session_id) and str(b["player_id"]) == str(player_id)
    ]


def block(supabase: Client, player_id: UUID | str, blocked_id: UUID | str) -> None:
    pid, other = str(player_id), str(blocked_id)
    if runs_until(supabase, pid) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ต้องมี Pass ที่ยังใช้ได้ก่อน")
    night = night_of(supabase, pid)
    if night is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="เช็คอินคืนนี้ก่อน แล้วค่อยเลือก")
    if other == pid or other not in checked_in(supabase, night["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบคนนี้ในคืนนี้")
    mine = blocks_of(supabase, night["id"], pid)
    if other in mine:
        return
    if len(mine) >= BLOCKS_PER_NIGHT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"เลือกได้คืนละ {BLOCKS_PER_NIGHT} คน — ยกเลิกคนเดิมก่อน"
        )
    supabase.table("pass_blocks").insert({"session_id": str(night["id"]), "player_id": pid, "blocked_id": other}).execute()


def unblock(supabase: Client, player_id: UUID | str, blocked_id: UUID | str) -> None:
    night = night_of(supabase, player_id)
    if night is None:
        return
    supabase.table("pass_blocks").delete().eq("session_id", str(night["id"])).eq("player_id", str(player_id)).eq(
        "blocked_id", str(blocked_id)
    ).execute()


def blocked_partners(supabase: Client, session_id: UUID | str, pass_holders: set[str]) -> set[frozenset[UUID]]:
    """Pairs who must not be partnered tonight: the blocks of members whose
    pass still runs."""
    return {
        frozenset((UUID(str(b["player_id"])), UUID(str(b["blocked_id"]))))
        for b in rows(supabase.table("pass_blocks").select("*").eq("session_id", str(session_id)).execute())
        if str(b["session_id"]) == str(session_id) and str(b["player_id"]) in pass_holders
    }
