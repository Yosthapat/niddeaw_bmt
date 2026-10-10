"""Whether a session still accepts changes.

Closing a session is what bills everyone in it (see billing_service), so
anything added afterwards is work nobody is charged for: a player checked
into last week's closed session never appears on a bill, and a match
created there changes no one's total. The admin UI lists closed sessions
in the picker — by design, so old nights can be looked at — which makes
picking one and carrying on an easy mistake to make on a club night.
"""

from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows


def ensure_session_open(supabase: Client, session_id: UUID) -> None:
    """Raises 404 if the session is gone, 409 if it has been closed."""
    result = (
        supabase.table("sessions").select("status").eq("id", str(session_id)).limit(1).execute()
    )
    session_rows = rows(result)
    if not session_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session_rows[0]["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session นี้ปิดไปแล้ว — เปิด session ใหม่ก่อน",
        )
