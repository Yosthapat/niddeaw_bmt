from uuid import UUID

from fastapi import APIRouter, Query

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.match import Match

router = APIRouter(prefix="/api/matches", tags=["public-matches"])


@router.get("", response_model=list[Match])
def list_matches(
    supabase: SupabaseDep,
    session_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Match]:
    query = (
        supabase.table("matches")
        .select("*")
        .eq("status", "completed")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if session_id is not None:
        query = query.eq("session_id", str(session_id))
    result = query.execute()
    return [Match.model_validate(row) for row in rows(result)]
