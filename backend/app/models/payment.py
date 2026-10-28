from pydantic import BaseModel

from app.models.club_settings import PaymentMethod


class PaymentInfoResponse(BaseModel):
    method: PaymentMethod
    amount: float
    data_uri: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
