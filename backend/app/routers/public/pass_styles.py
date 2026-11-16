"""Who wears a pass look right now: the frame round their picture and the
face of their profile card (services/pass_perks.py)."""

from fastapi import APIRouter

from app.deps import SupabaseDep
from app.models.niddeaw_pass import PassLook
from app.services import pass_perks

router = APIRouter(prefix="/api/pass-styles", tags=["public-pass-styles"])


@router.get("", response_model=dict[str, PassLook])
def pass_styles(supabase: SupabaseDep) -> dict[str, PassLook]:
    """{player_id: {frame, card}}; members wearing nothing are left out."""
    return {pid: PassLook.model_validate(look) for pid, look in pass_perks.looks(supabase).items()}
