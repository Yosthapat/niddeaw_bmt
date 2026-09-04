from typing import Literal

from pydantic import BaseModel

PromptPayType = Literal["phone", "national_id", "ewallet"]
PaymentMethod = Literal["promptpay", "bank_account", "bank_account_qr", "uploaded_qr"]


class ClubSettingsUpdate(BaseModel):
    payment_method: PaymentMethod | None = None
    promptpay_id: str | None = None
    promptpay_type: PromptPayType | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    default_court_fee_per_person: float | None = None
    default_shuttlecock_price_per_game: float | None = None


class ClubSettings(BaseModel):
    payment_method: PaymentMethod
    promptpay_id: str
    promptpay_type: PromptPayType
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    uploaded_qr_url: str | None = None
    default_court_fee_per_person: float
    default_shuttlecock_price_per_game: float
