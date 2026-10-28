from fastapi import APIRouter

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.sponsor import Sponsor

router = APIRouter(prefix="/api/sponsors", tags=["public-sponsors"])


@router.get("", response_model=list[Sponsor])
def list_visible_sponsors(supabase: SupabaseDep) -> list[Sponsor]:
    """The home page's logo band, in the order the admin set."""
    result = (
        supabase.table("sponsors")
        .select("*")
        .eq("is_visible", True)
        .order("sort_order")
        .order("created_at")
        .execute()
    )
    return [Sponsor.model_validate(row) for row in rows(result)]
