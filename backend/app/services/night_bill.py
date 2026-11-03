"""One member's bill for one night: worked out, and charged.

The admin's "bill this player" button (routers/admin/billing.py) and a
member checking themselves out from LINE (routers/line.py) both end here,
so the two can't disagree about what someone owes: a flat court fee plus a
shuttlecock cost per completed game (services/billing_service.py), nothing
at all for someone who never played.
"""

import contextlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.services import billing_service, queue_service
from app.services.image_service import storage_path_from_url

SLIP_BUCKET = "shop"  # where the shop's order slips already go

BUSY = "คนนี้ยังมีแมตช์ที่ยังไม่จบ (กำลังแข่ง/รอเริ่ม) — บันทึกผลหรือยกเลิกแมตช์ก่อน"


def night(supabase: Client, session_id: UUID) -> dict[str, Any]:
    found = rows(
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return found[0]


def is_busy(supabase: Client, session_id: UUID, player_id: UUID) -> bool:
    """A match of theirs is queued or on court: their bill isn't final."""
    unfinished = queue_service.players_in_progress(
        supabase, session_id
    ) | queue_service.players_in_queued_matches(supabase, session_id)
    return player_id in unfinished


def so_far(supabase: Client, session: dict[str, Any], player_id: UUID) -> tuple[int, float]:
    """Games they have finished tonight, and what that comes to."""
    matches = rows(
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids")
        .eq("session_id", str(session["id"]))
        .eq("status", "completed")
        .execute()
    )
    games = billing_service.count_games_played(str(player_id), matches)
    amount = billing_service.compute_amount_calc(
        games, session["court_fee_per_person"], session["shuttlecock_price_per_game"]
    )
    return games, amount


def bill_one(supabase: Client, session_id: UUID, player_id: UUID) -> dict[str, Any]:
    """Bill one attendee now and check them out, independent of the
    session's status — they went home early and shouldn't wait for
    everyone else. Refused while they still have a match outstanding,
    queued or on court: the bill counts completed games, so charging now
    would miss the games they are about to play. Paid status and any
    adjustment are left as they are (upsert without those columns)."""
    session = night(supabase, session_id)
    if is_busy(supabase, session_id, player_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=BUSY)
    games, amount = so_far(supabase, session, player_id)
    now_iso = datetime.now(UTC).isoformat()
    # Being billed ends their night, so close the check-in too — the same
    # thing closing the session does for everyone at once.
    supabase.table("checkins").update({"checkout_time": now_iso}).eq(
        "session_id", str(session_id)
    ).eq("player_id", str(player_id)).is_("checkout_time", "null").execute()
    result = (
        supabase.table("billings")
        .upsert(
            {
                "session_id": str(session_id),
                "player_id": str(player_id),
                "game_count": games,
                "amount_calc": amount,
                "updated_at": now_iso,
            },
            on_conflict="session_id,player_id",
        )
        .execute()
    )
    return rows(result)[0]


def forget_slip(supabase: Client, url: str | None) -> None:
    """Best effort: a transfer slip nothing points at any more."""
    path = storage_path_from_url(url, SLIP_BUCKET) if url else None
    if path:
        with contextlib.suppress(Exception):
            supabase.storage.from_(SLIP_BUCKET).remove([path])
