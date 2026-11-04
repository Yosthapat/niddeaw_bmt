from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.fields import Baht

PaidStatus = Literal["unpaid", "paid"]


class BillingAdjust(BaseModel):
    amount_adjusted: Baht | None = None


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
    slip_url: str | None = None
    """A transfer slip the member attached from LINE, for the admin to check."""
    slip_sent_at: datetime | None = None
    slip_rejected_at: datetime | None = None
    """The admin refused their last slip; they are asked for a new one."""
    credit_used: int = 0
    """How much of the bill the member paid with club credit; the slip, if
    any, is for the rest."""

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
    credit_amount: float = 0
    """Of total_amount, what members paid with club credit — its baht was
    counted when they topped up, so it is not money in again."""
    paid_cash: float = 0
    """Dues money actually received: paid bills less the credit on them."""
