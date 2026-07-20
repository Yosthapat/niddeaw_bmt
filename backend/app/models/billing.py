from datetime import date, datetime
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
    game_count: int
    amount_calc: float
    amount_adjusted: float | None = None
    paid_status: PaidStatus
    promptpay_ref: str | None = None
    updated_at: datetime

    @property
    def effective_amount(self) -> float:
        return self.amount_adjusted if self.amount_adjusted is not None else self.amount_calc


class DailyRevenue(BaseModel):
    """One day's billing summary — grouped by the session's date."""

    date: date
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    session_count: int
    billing_count: int
