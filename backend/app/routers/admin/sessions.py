from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.session import Session, SessionCreate, SessionUpdate

router = APIRouter(prefix="/api/admin/sessions", tags=["admin-sessions"])


@router.get("", response_model=list[Session])
def list_sessions(supabase: SupabaseDep, admin: AdminDep) -> list[Session]:
    result = supabase.table("sessions").select("*").order("date", desc=True).execute()
    return [Session.model_validate(row) for row in rows(result)]


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, supabase: SupabaseDep, admin: AdminDep) -> Session:
    row = {**payload.model_dump(mode="json"), "status": "open", "created_by": str(admin.admin_id)}
    result = supabase.table("sessions").insert(row).execute()
    return Session.model_validate(rows(result)[0])


@router.patch("/{session_id}", response_model=Session)
def update_session(
    session_id: UUID, payload: SessionUpdate, supabase: SupabaseDep, admin: AdminDep
) -> Session:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = supabase.table("sessions").update(updates).eq("id", str(session_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Session.model_validate(result_rows[0])


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Permanently deletes a session — e.g. it was created by mistake.
    checkins/matches/billings/pairing_history all reference sessions with
    ON DELETE CASCADE, so they're removed automatically."""
    result = supabase.table("sessions").delete().eq("id", str(session_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
