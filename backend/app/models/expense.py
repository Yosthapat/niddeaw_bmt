from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.fields import Note, PositiveBaht

ExpenseCategory = Literal["court_fee", "shuttlecock", "jersey", "other"]


class ExpenseCreate(BaseModel):
    expense_date: date
    category: ExpenseCategory
    category_other: Note | None = None
    amount: PositiveBaht
    paid_by: UUID
    note: Note | None = None


class ExpenseUpdate(BaseModel):
    expense_date: date | None = None
    category: ExpenseCategory | None = None
    category_other: Note | None = None
    amount: PositiveBaht | None = None
    paid_by: UUID | None = None
    note: Note | None = None


class Expense(BaseModel):
    id: UUID
    expense_date: date
    category: ExpenseCategory
    category_other: str | None = None
    amount: float
    paid_by: UUID
    receipt_url: str | None = None
    note: str | None = None
    is_paid: bool = False
    paid_at: datetime | None = None
    created_by: UUID
    created_at: datetime


class MonthlyExpenseSummary(BaseModel):
    """month is "YYYY-MM" — a plain string, not a date, since it has no day."""

    month: str
    total_amount: float
    paid_amount: float
    by_category: dict[str, float]
    expense_count: int
