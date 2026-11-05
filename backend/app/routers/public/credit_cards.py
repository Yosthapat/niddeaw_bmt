"""Who holds a pink or black credit card right now, for the small card
shown by their name (services/credit_card_service.py)."""

from fastapi import APIRouter

from app.deps import SupabaseDep
from app.services import credit_card_service

router = APIRouter(prefix="/api/credit-cards", tags=["public-credit-cards"])


@router.get("", response_model=dict[str, credit_card_service.Tier])
def credit_cards(supabase: SupabaseDep) -> dict[str, credit_card_service.Tier]:
    """{player_id: "pink" | "black"}; members without a card are left out."""
    return {pid: c.tier for pid, c in credit_card_service.all_cards(supabase).items()}
