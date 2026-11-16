"""The tournament as anyone sees it on /tournament: the event, its levels,
how full each is, and the teams that hold a place — nicknames and avatars
only, never a real name or phone."""

from uuid import UUID

from fastapi import APIRouter, Response

from app.deps import SupabaseDep
from app.models.tournament import PublicTournament
from app.services import tournament_cache
from app.services import tournament_service as ts
from app.services import tournament_views as views

router = APIRouter(prefix="/api/tournament", tags=["tournament"])


@router.get("", response_model=PublicTournament | None)
def current_tournament(supabase: SupabaseDep, id: UUID | None = None) -> Response:
    """None when no tournament is past its draft: the page shows "coming
    soon" then. The JSON is made once per cached copy and handed out as is
    (tournament_cache.Held).

    With ?id=, that one tournament, whatever its status: the TV board's
    preview link (/tournament/board?t=…), so a draft set up to rehearse the
    day can be shown on the screen while the real one stays on the public
    pages. The same public view — nothing private — and not cached: it is
    one screen, not a hall of phones."""
    if id is not None:
        model = views.public_tournament(supabase, ts.tournament(supabase, str(id)))
        return Response(content=model.model_dump_json(), media_type="application/json")
    held = tournament_cache.current(supabase)
    body = held.json(supabase) if held else b"null"
    return Response(content=body, media_type="application/json")
