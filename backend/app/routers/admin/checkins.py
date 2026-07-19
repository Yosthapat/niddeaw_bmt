from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.checkin import Checkin, CheckinCreate

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
