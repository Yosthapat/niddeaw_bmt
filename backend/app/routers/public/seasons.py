from fastapi import APIRouter

from app.deps import SupabaseDep
from app.models.season import Season
from app.services import season_service

router = APIRouter(prefix="/api/seasons", tags=["public-seasons"])


@router.get("", response_model=list[Season])
def list_seasons(supabase: SupabaseDep) -> list[Season]:
    """Every season the club has played, oldest first. Empty before the
    first session exists.

    The season definition lives here rather than in the frontend so a
    client can't disagree with the backend about which matches belong to
    "season 2".
    """
    return [
        Season(
            number=span.number,
            year=span.year,
            start_date=span.start_date,
            end_date=span.end_date,
            is_current=span.is_current,
        )
        for span in season_service.fetch_seasons(supabase)
    ]
