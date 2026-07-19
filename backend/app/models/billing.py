from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

PaidStatus = Literal["unpaid", "paid"]


class BillingAdjust(BaseModel):
    amount_adjusted: float | None = None


class BillingMarkPaid(BaseModel):
    paid_status: PaidStatus


class Billing(BaseModel):
    id: UUID
    session_id: UUID
    player_id: UUID
    hours_played: float
    amount_calc: float
    amount_adjusted: float | None = None
    paid_status: PaidStatus
    promptpay_ref: str | None = None
    updated_at: datetime

    @property
    def effective_amount(self) -> float:
        return self.amount_adjusted if self.amount_adjusted is not None else self.amount_calc
