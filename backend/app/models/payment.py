from pydantic import BaseModel

from app.models.club_settings import PaymentMethod


class PaymentInfoResponse(BaseModel):
    method: PaymentMethod
    amount: float
    data_uri: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    qr_modules: list[str] | None = None
    """The same QR as data_uri, as rows of 0/1, when the club's QR is one
    we generate (PromptPay, bank details) — the page draws it as the
    club's QR card. None for an uploaded QR image."""
