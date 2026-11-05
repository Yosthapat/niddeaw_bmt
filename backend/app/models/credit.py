from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.player import Player

TopupStatus = Literal["pending", "approved", "rejected"]
LedgerKind = Literal["topup", "bill", "refund", "adjust"]

Credits = Annotated[int, Field(ge=1, le=100000)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class CreditPackage(BaseModel):
    id: UUID
    credits: int
    price: float
    is_active: bool = True
    sort_order: int = 0


class CreditPackageIn(BaseModel):
    credits: Credits
    price: Annotated[float, Field(gt=0, le=100000)]
    is_active: bool = True
    sort_order: Annotated[int, Field(ge=0, le=1000)] = 0

    @model_validator(mode="after")
    def _not_more_than_it_buys(self) -> "CreditPackageIn":
        if self.price > self.credits:
            raise ValueError("ราคาต้องไม่เกินจำนวนเครดิตที่ได้")
        return self


class CreditPackageUpdate(BaseModel):
    credits: Credits | None = None
    price: Annotated[float, Field(gt=0, le=100000)] | None = None
    is_active: bool | None = None
    sort_order: Annotated[int, Field(ge=0, le=1000)] | None = None


class CreditTopup(BaseModel):
    id: UUID
    player_id: UUID
    credits: int
    price: float
    slip_url: str | None = None
    slip_sent_at: datetime | None = None
    status: TopupStatus
    note: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class CreditTopupAdmin(CreditTopup):
    player_nickname: str
    player_code: str


class LedgerEntry(BaseModel):
    id: UUID
    delta: int
    balance_after: int
    kind: LedgerKind
    cash: float | None = None
    note: str | None = None
    created_at: datetime


class TopupIn(BaseModel):
    package_id: UUID


class TopupReject(BaseModel):
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


class CreditCard(BaseModel):
    """The pink or black card a member holds while their credit lasts
    (services/credit_card_service.py). `since` changes when a new card
    is given, so LINE can celebrate each one once."""

    tier: Literal["pink", "black"]
    since: str


class LineCredit(BaseModel):
    """A member's own credit, as the /line page and their profile show it."""

    player: Player
    balance: int
    card: CreditCard | None = None
    packages: list[CreditPackage]
    # The one top-up waiting, if any — with or without its slip yet.
    pending: CreditTopup | None = None
    # The last one refused, so they can see why.
    rejected: CreditTopup | None = None
    history: list[LedgerEntry]


class CreditAdjust(BaseModel):
    """An admin's change to a balance: cash taken at the court, a refund,
    a correction. Always with a reason."""

    delta: Annotated[int, Field(ge=-100000, le=100000)]
    # Baht that moved with it, if any: received for credit added, paid back
    # for credit taken off. Left out when no money changed hands.
    cash: Annotated[float, Field(ge=0, le=100000)] | None = None
    note: Reason

    @model_validator(mode="after")
    def _not_zero(self) -> "CreditAdjust":
        if self.delta == 0:
            raise ValueError("ใส่จำนวนเครดิตที่ต้องการปรับ")
        return self


class MemberCredit(BaseModel):
    player_id: UUID
    nickname: str
    member_code: str
    balance: int


class CreditBalances(BaseModel):
    outstanding: int
    members: list[MemberCredit]


class CreditDay(BaseModel):
    date: str
    cash: float


class CreditSummary(BaseModel):
    """For the dashboard. cash_in is baht received for credit (top-ups and
    cash an admin took), cash_out what was paid back; outstanding is credit
    members still hold — money in the account that is still theirs."""

    cash_in: float
    cash_out: float
    outstanding: int
    pending_topups: int
    daily: list[CreditDay]


class MemberLedger(BaseModel):
    player: Player
    balance: int
    history: list[LedgerEntry]
