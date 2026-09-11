from uuid import UUID

from fastapi import APIRouter

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.matchmaking import LiveQueueResponse, WaitingEntry
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
            queued=[],
            waiting=[],
            avg_match_duration_minutes=0.0,
        )

    session_id = UUID(session_rows[0]["id"])
    queue = queue_service.build_queue(supabase, session_id)

    # Auto-suggested pairings stay admin-only (see LiveQueueResponse), but the
    # players sitting in them are still waiting for a court — fold them into
    # the waiting list, ahead of the leftovers not in a group yet, so they
    # don't disappear from the public view entirely.
    waiting: list[WaitingEntry] = []
    # Each suggestion group is one prospective match, so the Nth group waits
    # roughly N match-lengths. Counting player slots instead (the admin
    # queue's flat position * avg) would quote the fourth group ~16 matches
    # of waiting, which on a 3-hour session reads as longer than the session.
    for slot, suggestion in enumerate(queue.suggestions, start=1):
        for pid in (*suggestion.team1_player_ids, *suggestion.team2_player_ids):
            waiting.append(
                WaitingEntry(
                    player_id=pid,
                    queue_position=len(waiting) + 1,
                    estimated_wait_minutes=slot * queue.avg_match_duration_minutes,
                )
            )
    # Leftovers sit behind every suggested group — offset them by the group
    # count, or they'd read as getting on court sooner than grouped players.
    for entry in queue.waiting:
        waiting.append(
            WaitingEntry(
                player_id=entry.player_id,
                queue_position=len(waiting) + 1,
                estimated_wait_minutes=(len(queue.suggestions) + entry.queue_position)
                * queue.avg_match_duration_minutes,
            )
        )

    return LiveQueueResponse(
        session_id=session_id,
        session_date=session_rows[0]["date"],
        location=session_rows[0]["location"],
        in_progress=queue.in_progress,
        queued=queue.queued,
        waiting=waiting,
        avg_match_duration_minutes=queue.avg_match_duration_minutes,
    )
