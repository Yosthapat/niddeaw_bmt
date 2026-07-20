from uuid import UUID

from fastapi import APIRouter

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.matchmaking import LiveQueueResponse
from app.services import queue_service

router = APIRouter(prefix="/api/live", tags=["public-live"])


@router.get("", response_model=LiveQueueResponse)
def live_status(supabase: SupabaseDep) -> LiveQueueResponse:
    """Read-only view of the currently open session's queue — lets a player
    see if their match is in progress or how many groups are ahead of them,
    without needing to log in or know a session_id."""
    session_result = (
        supabase.table("sessions")
        .select("id, date, location")
        .eq("status", "open")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    session_rows = rows(session_result)
    if not session_rows:
        return LiveQueueResponse(
            session_id=None,
            session_date=None,
            location=None,
            in_progress=[],
            suggestions=[],
            waiting=[],
            avg_match_duration_minutes=0.0,
        )

    session_id = UUID(session_rows[0]["id"])
    queue = queue_service.build_queue(supabase, session_id)
    return LiveQueueResponse(
        session_id=session_id,
        session_date=session_rows[0]["date"],
        location=session_rows[0]["location"],
        in_progress=queue.in_progress,
        suggestions=queue.suggestions,
        waiting=queue.waiting,
        avg_match_duration_minutes=queue.avg_match_duration_minutes,
    )
