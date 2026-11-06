"""Checking a member in to a night, whoever does it.

The admin at the door (routers/admin/checkins.py) and the member scanning
the QR through LINE (routers/line.py) both end up here, so a check-in
means the same thing either way: one per member per night, re-opened if
they had checked out, and never into a night that is already billed.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.services.session_state import ensure_session_open

Via = Literal["admin", "line", "gps"]


def check_in(supabase: Client, session_id: UUID, player_id: UUID, via: Via) -> dict[str, Any]:
    """Check a member in — or back in.

    A night has one check-in per member (uq_checkins_session_player), and
    someone who checked out — went home early, was billed, was checked out
    by mistake — is back on the "not checked in" list. Checking them in
    again re-opens that same check-in rather than adding a second one,
    which the database would refuse. Someone already in (a double tap, two
    admins at the door, a member who scans twice) gets back the check-in
    they already have. `via` is who did the latest check-in."""
    # A closed session has already been billed, so a check-in added now
    # would be a player on the court with no bill.
    ensure_session_open(supabase, session_id)
    player = rows(
        supabase.table("players").select("id").eq("id", str(player_id)).limit(1).execute()
    )
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    existing = rows(
        supabase.table("checkins")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("player_id", str(player_id))
        .limit(1)
        .execute()
    )
    if existing:
        if existing[0].get("checkout_time") is None:
            return existing[0]
        reopened = (
            supabase.table("checkins")
            .update({"checkout_time": None, "via": via})
            .eq("id", str(existing[0]["id"]))
            .execute()
        )
        return rows(reopened)[0]
    row = {
        "session_id": str(session_id),
        "player_id": str(player_id),
        "checkin_time": datetime.now(UTC).isoformat(),
        "via": via,
    }
    return rows(supabase.table("checkins").insert(row).execute())[0]
