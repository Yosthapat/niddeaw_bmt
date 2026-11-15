"""The tournament as anyone sees it on /tournament: the event, its levels,
how full each is, and the teams that hold a place — nicknames and avatars
only, never a real name or phone."""

from fastapi import APIRouter

from app.deps import SupabaseDep
from app.models.tournament import PublicTournament
from app.services import tournament_service as ts
from app.services import tournament_views as views

router = APIRouter(prefix="/api/tournament", tags=["tournament"])


@router.get("", response_model=PublicTournament | None)
def current_tournament(supabase: SupabaseDep) -> PublicTournament | None:
    """None when no tournament is past its draft: the page shows "coming
    soon" then."""
    row = ts.current(supabase)
    if row is None:
        return None
    ts.sweep(supabase, str(row["id"]))
    return views.public_tournament(supabase, row)
