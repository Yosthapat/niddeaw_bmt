"""What the home page's two wallet cards show: the credit packages on sale
and what the Niddeaw Pass costs. Buying either still happens on the /line
page, where the member is known; this only reads prices."""

from fastapi import APIRouter

from app.deps import SupabaseDep
from app.models.credit import WalletOffer
from app.services import credit_service, pass_service

router = APIRouter(prefix="/api/wallet-offer", tags=["public-wallet"])


@router.get("", response_model=WalletOffer)
def wallet_offer(supabase: SupabaseDep) -> WalletOffer:
    return WalletOffer(packages=credit_service.active_packages(supabase), pass_price=pass_service.price(supabase))
