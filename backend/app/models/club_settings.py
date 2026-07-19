from typing import Literal

from pydantic import BaseModel

PromptPayType = Literal["phone", "national_id", "ewallet"]


class ClubSettingsUpdate(BaseModel):
    promptpay_id: str | None = None
    promptpay_type: PromptPayType | None = None
    default_court_fee_per_person: float | None = None
    default_shuttlecock_price_per_game: float | None = None


class ClubSettings(BaseModel):
    promptpay_id: str
    promptpay_type: PromptPayType
    default_court_fee_per_person: float
    default_shuttlecock_price_per_game: float
