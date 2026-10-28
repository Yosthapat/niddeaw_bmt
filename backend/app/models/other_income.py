from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.fields import Name, Note, PositiveBaht

IncomeSource = Literal["sponsor", "investment", "other"]


class OtherIncomeCreate(BaseModel):
    income_date: date
    source: IncomeSource
    source_name: Name
    amount: PositiveBaht
    note: Note | None = None


class OtherIncomeUpdate(BaseModel):
    income_date: date | None = None
    source: IncomeSource | None = None
    source_name: Name | None = None
    amount: PositiveBaht | None = None
    note: Note | None = None


class OtherIncome(BaseModel):
    id: UUID
    income_date: date
    source: IncomeSource
    source_name: str
    amount: float
    note: str | None = None
    slip_url: str | None = None
    created_by: UUID
    created_at: datetime
