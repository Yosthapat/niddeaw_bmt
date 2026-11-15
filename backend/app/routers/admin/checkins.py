from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.checkin import Checkin, CheckinCreate, CheckinPause
from app.services import checkin_service

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
    """Check a member in — or back in (services/checkin_service.py)."""
    return Checkin.model_validate(
        checkin_service.check_in(supabase, payload.session_id, payload.player_id, "admin")
    )


@router.post("/{checkin_id}/checkout", response_model=Checkin)
def check_out(checkin_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> Checkin:
    result = (
        supabase.table("checkins")
        .update({"checkout_time": datetime.now(UTC).isoformat()})
        .eq("id", str(checkin_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkin not found")
    return Checkin.model_validate(result_rows[0])


def _set_paused(supabase: SupabaseDep, payload: CheckinPause, paused_at: str | None) -> Checkin:
    result = (
        supabase.table("checkins")
        .update({"paused_at": paused_at})
        .eq("session_id", str(payload.session_id))
        .eq("player_id", str(payload.player_id))
        .is_("checkout_time", "null")
        .execute()
    )
    found = rows(result)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ผู้เล่นคนนี้ไม่ได้เช็คอินอยู่")
    return Checkin.model_validate(found[0])


@router.post("/pause", response_model=Checkin)
def pause(payload: CheckinPause, supabase: SupabaseDep, admin: AdminDep) -> Checkin:
    """Rest a member who is in but needs a break: they stay checked in (and
    billed as usual) and are left out of the suggested pairings until
    resumed."""
    return _set_paused(supabase, payload, datetime.now(UTC).isoformat())


@router.post("/resume", response_model=Checkin)
def resume(payload: CheckinPause, supabase: SupabaseDep, admin: AdminDep) -> Checkin:
    """Back from a rest: in the queue again, as anyone else waiting."""
    return _set_paused(supabase, payload, None)
