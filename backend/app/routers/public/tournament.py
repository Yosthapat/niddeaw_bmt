"""The tournament as anyone sees it on /tournament: the event, its levels,
how full each is, and the teams that hold a place — nicknames and avatars
only, never a real name or phone."""

from fastapi import APIRouter, Response

from app.deps import SupabaseDep
from app.models.tournament import PublicTournament
from app.services import tournament_cache

router = APIRouter(prefix="/api/tournament", tags=["tournament"])


@router.get("", response_model=PublicTournament | None)
def current_tournament(supabase: SupabaseDep) -> Response:
    """None when no tournament is past its draft: the page shows "coming
    soon" then. The JSON is made once per cached copy and handed out as is
    (tournament_cache.Held)."""
    held = tournament_cache.current(supabase)
    body = held.json(supabase) if held else b"null"
    return Response(content=body, media_type="application/json")
