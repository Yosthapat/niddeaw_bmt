from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.fields import Baht, EditForm, Name

SessionStatus = Literal["open", "closed"]


class SessionCreate(BaseModel):
    date: date
    location: Name
    court_fee_per_person: Baht
    shuttlecock_price_per_game: Baht


class SessionUpdate(EditForm):
    NOT_NULL = frozenset({"location", "court_fee_per_person", "shuttlecock_price_per_game", "status"})

    location: Name | None = None
    court_fee_per_person: Baht | None = None
    shuttlecock_price_per_game: Baht | None = None
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
