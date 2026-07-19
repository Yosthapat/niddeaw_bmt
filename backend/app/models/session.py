from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SessionStatus = Literal["open", "closed"]


class SessionCreate(BaseModel):
    date: date
    location: str
    rate_per_hour: float


class SessionUpdate(BaseModel):
    location: str | None = None
    rate_per_hour: float | None = None
    status: SessionStatus | None = None


class Session(BaseModel):
    id: UUID
    date: date
    location: str
    rate_per_hour: float
    status: SessionStatus
    created_by: UUID
    created_at: datetime
