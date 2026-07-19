from typing import Literal

from pydantic import BaseModel

PromptPayType = Literal["phone", "national_id", "ewallet"]


class ClubSettingsUpdate(BaseModel):
    promptpay_id: str | None = None
    promptpay_type: PromptPayType | None = None
    default_rate_per_hour: float | None = None


class ClubSettings(BaseModel):
    promptpay_id: str
    promptpay_type: PromptPayType
    default_rate_per_hour: float
