from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SessionStatus = Literal["open", "closed"]


class SessionCreate(BaseModel):
    date: date
    location: str
    court_fee_per_person: float
    shuttlecock_price_per_game: float


class SessionUpdate(BaseModel):
    location: str | None = None
    court_fee_per_person: float | None = None
    shuttlecock_price_per_game: float | None = None
    status: SessionStatus | None = None


class Session(BaseModel):
    id: UUID
    date: date
    location: str
    court_fee_per_person: float
    shuttlecock_price_per_game: float
    status: SessionStatus
    created_by: UUID
    created_at: datetime
