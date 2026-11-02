from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.checkin import Checkin, CheckinCreate
from app.services.session_state import ensure_session_open

router = APIRouter(prefix="/api/admin/checkins", tags=["admin-checkins"])


@router.get("", response_model=list[Checkin])
def list_checkins(
    supabase: SupabaseDep, admin: AdminDep, session_id: UUID, active_only: bool = False
) -> list[Checkin]:
    query = supabase.table("checkins").select("*").eq("session_id", str(session_id))
    if active_only:
        query = query.is_("checkout_time", "null")
    result = query.execute()
    return [Checkin.model_validate(row) for row in rows(result)]


@router.post("", response_model=Checkin, status_code=status.HTTP_201_CREATED)
def check_in(payload: CheckinCreate, supabase: SupabaseDep, admin: AdminDep) -> Checkin:
    """Check a member in — or back in.

    A night has one check-in per member (uq_checkins_session_player), and
    someone who checked out — went home early, was billed, was checked out
    by mistake — is back on the "not checked in" list. Tapping them again
    re-opens that same check-in rather than adding a second one, which the
    database would refuse. Tapping someone already in (a double tap, two
    admins at the door) gives back the check-in they already have."""
    # A closed session has already been billed, so a check-in added now
    # would be a player on the court with no bill.
    ensure_session_open(supabase, payload.session_id)
    player = rows(supabase.table("players").select("id").eq("id", str(payload.player_id)).limit(1).execute())
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    existing = rows(
        supabase.table("checkins")
        .select("*")
        .eq("session_id", str(payload.session_id))
        .eq("player_id", str(payload.player_id))
        .limit(1)
        .execute()
    )
    if existing:
        if existing[0].get("checkout_time") is None:
            return Checkin.model_validate(existing[0])
        reopened = (
            supabase.table("checkins").update({"checkout_time": None}).eq("id", str(existing[0]["id"])).execute()
        )
        return Checkin.model_validate(rows(reopened)[0])
    row = {
        "session_id": str(payload.session_id),
        "player_id": str(payload.player_id),
        "checkin_time": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("checkins").insert(row).execute()
    return Checkin.model_validate(rows(result)[0])


@router.post("/{checkin_id}/checkout", response_model=Checkin)
def check_out(checkin_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> Checkin:
    result = (
        supabase.table("checkins")
        .update({"checkout_time": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(checkin_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkin not found")
    return Checkin.model_validate(result_rows[0])
