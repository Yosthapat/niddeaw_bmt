"""NIDDEAW CUP (docs/tournament-spec.md): the event, its levels, the teams
that sign up and the event's own money. Kept apart from the club's models
on purpose — none of this is club money or a club night."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.fields import EditForm, PositiveBaht

TournamentStatus = Literal["draft", "open", "closed", "running", "done"]
TeamStatus = Literal[
    "invited", "awaiting_payment", "slip_review", "confirmed", "waitlist", "cancelled", "withdrawn"
]
PayStatus = Literal["unpaid", "slip_sent", "paid", "rejected", "refunded"]
PaidVia = Literal["transfer", "cash"]
PromptPayKind = Literal["phone", "national_id", "ewallet"]
MoneyCategory = Literal[
    "entry_fee", "extra_shuttles", "sponsor", "other_income",
    "court", "shuttle", "trophy", "prize", "staff", "photo", "refund", "coupon_refund", "other",
]  # fmt: skip

TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
# The rule shop_orders.guest_phone already uses: a Thai number, 9–10 digits.
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^0[0-9]{8,9}$")]
Fee = Annotated[int, Field(ge=0, le=100_000)]
Elo = Annotated[int, Field(ge=0, le=4000)]
TeamSize = Literal[16, 24, 32]


# --- the event --------------------------------------------------------------


class Level(BaseModel):
    id: UUID
    name: str
    min_elo: int | None = None
    max_elo: int | None = None
    max_teams: int
    cut_24: bool = False
    rules: str = ""
    sort: int = 0


class Tournament(BaseModel):
    id: UUID
    name: str
    starts_on: date
    venue: str = ""
    entry_fee: int
    shuttle_fee: int
    coupons_per_set: int
    extra_set_price: int
    coupon_refund_price: int
    promptpay_id: str | None = None
    promptpay_type: PromptPayKind | None = None
    account_name: str | None = None
    opens_at: datetime | None = None
    closes_at: datetime
    min_games: int
    courts: int | None = None
    status: TournamentStatus
    created_at: datetime | None = None
    day_start: str = "09:00"
    group_minutes: int = 20
    ko_minutes: int = 30
    rest_minutes: int = 10
    schedule_published_at: datetime | None = None
    levels: list[Level] = []
    # Once anyone has paid, the price is fixed, so nobody pays a different one.
    fees_locked: bool = False


class TournamentCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    starts_on: date
    venue: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    closes_at: datetime
    opens_at: datetime | None = None


class TournamentUpdate(EditForm):
    NOT_NULL = frozenset(
        {"name", "starts_on", "venue", "entry_fee", "shuttle_fee", "coupons_per_set",
         "extra_set_price", "coupon_refund_price", "closes_at", "min_games", "status",
         "day_start", "group_minutes", "ko_minutes", "rest_minutes"}
    )  # fmt: skip

    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)] | None
    ) = None
    starts_on: date | None = None
    venue: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    entry_fee: Fee | None = None
    shuttle_fee: Fee | None = None
    coupons_per_set: Annotated[int, Field(ge=1, le=50)] | None = None
    extra_set_price: Fee | None = None
    coupon_refund_price: Annotated[int, Field(ge=0, le=10_000)] | None = None
    promptpay_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = (
        None
    )
    promptpay_type: PromptPayKind | None = None
    account_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = (
        None
    )
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    min_games: Annotated[int, Field(ge=0, le=100)] | None = None
    courts: Annotated[int, Field(ge=1, le=60)] | None = None
    status: TournamentStatus | None = None
    day_start: (
        Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9](:00)?$")] | None
    ) = None
    group_minutes: Annotated[int, Field(ge=5, le=120)] | None = None
    ko_minutes: Annotated[int, Field(ge=5, le=120)] | None = None
    rest_minutes: Annotated[int, Field(ge=0, le=120)] | None = None


class LevelIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    min_elo: Elo | None = None
    max_elo: Elo | None = None
    max_teams: TeamSize = 16
    cut_24: bool = False
    rules: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""

    @model_validator(mode="after")
    def _range(self) -> "LevelIn":
        if self.min_elo is not None and self.max_elo is not None and self.min_elo >= self.max_elo:
            raise ValueError("ช่วง ELO ต้องเริ่มต่ำกว่าที่จบ")
        return self


class LevelUpdate(EditForm):
    NOT_NULL = frozenset({"name", "max_teams", "cut_24", "rules"})

    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)] | None
    ) = None
    min_elo: Elo | None = None
    max_elo: Elo | None = None
    max_teams: TeamSize | None = None
    cut_24: bool | None = None
    rules: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None


# --- who is in it -----------------------------------------------------------


class PublicPlayer(BaseModel):
    """What anyone may see of a player in a team: no real name, no phone."""

    nickname: str
    avatar_url: str | None = None
    elo_level: str | None = None


class PublicTeam(BaseModel):
    id: UUID | None = None
    name: str
    players: list[PublicPlayer]


class PublicGroup(BaseModel):
    label: str
    teams: list[PublicTeam]


class PublicLevel(Level):
    seats_taken: int = 0
    waitlist: int = 0
    teams: list[PublicTeam] = []
    # Only once the schedule is published.
    groups: list[PublicGroup] = []


class MatchSlot(BaseModel):
    """One side of a match: a team once known, else the place it comes from
    ("A1", "U3", "W12")."""

    slot: str
    team_id: UUID | None = None
    team_name: str | None = None
    # nicknames and avatars, as anywhere public — never a real name
    players: list[PublicPlayer] = []


class Match(BaseModel):
    id: UUID
    match_no: int
    level_id: UUID
    level_name: str
    stage: Literal["group", "ko"]
    bracket: Literal["upper", "lower"] | None = None
    round: int
    group_label: str | None = None
    a: MatchSlot
    b: MatchSlot
    est_start: datetime | None = None


class PublicTournament(BaseModel):
    id: UUID
    name: str
    starts_on: date
    venue: str
    entry_fee: int
    shuttle_fee: int
    coupons_per_set: int
    opens_at: datetime | None = None
    closes_at: datetime
    min_games: int
    status: TournamentStatus
    taking_entries: bool
    levels: list[PublicLevel]
    # The groups and the match list are shown once an admin publishes them;
    # until then the pages say "coming soon".
    schedule_published: bool = False
    matches: list[Match] = []


class Details(BaseModel):
    """A player's own name and phone, which they type in themselves."""

    first_name: PersonName
    last_name: PersonName
    phone: Phone


class Entrant(BaseModel):
    id: UUID
    player_id: UUID
    role: Literal["captain", "partner"]
    nickname: str
    avatar_url: str | None = None
    elo_level: str | None = None
    elo: int | None = None
    share: int
    pay_status: PayStatus
    paid_via: PaidVia | None = None
    slip_url: str | None = None
    slip_sent_at: datetime | None = None
    paid_at: datetime | None = None
    rejected_at: datetime | None = None
    refunded_at: datetime | None = None
    # Only to admins, and to the player about themselves.
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class Team(BaseModel):
    id: UUID
    tournament_id: UUID
    level_id: UUID
    level_name: str
    name: str
    status: TeamStatus
    expires_at: datetime | None = None
    invited_at: datetime | None = None
    accepted_at: datetime | None = None
    seat_held_at: datetime | None = None
    waitlist_at: datetime | None = None
    confirmed_at: datetime | None = None
    ended_at: datetime | None = None
    by_admin: bool = False
    entrants: list[Entrant]


class SlipCheckInfo(BaseModel):
    target_id: str
    status: Literal["ok", "duplicate", "no_qr", "not_slip", "unchecked"]
    used_before_who: str | None = None
    used_before_kind: str | None = None
    used_before_amount: float | None = None


class AdminTeam(Team):
    slip_checks: list[SlipCheckInfo] = []
    refund_owed: int = 0


# --- the LINE side ----------------------------------------------------------


class Me(BaseModel):
    player_id: UUID
    nickname: str
    avatar_url: str | None = None
    elo: int
    elo_level: str
    games: int
    games_needed: int
    level_id: UUID | None = None


class Candidate(BaseModel):
    player_id: UUID
    nickname: str
    avatar_url: str | None = None
    elo: int
    elo_level: str
    games: int
    eligible: bool
    taken: bool


class LineTournament(BaseModel):
    tournament: PublicTournament | None
    me: Me | None = None
    team: Team | None = None
    my_role: Literal["captain", "partner"] | None = None
    last_details: Details | None = None


class SignUpIn(Details):
    partner_id: UUID
    level_id: UUID
    team_name: TeamName


class RenameIn(BaseModel):
    team_name: TeamName


# --- the admin side ---------------------------------------------------------


class AdminPerson(Details):
    player_id: UUID


class AdminSignUpIn(BaseModel):
    level_id: UUID
    team_name: TeamName
    captain: AdminPerson
    partner: AdminPerson
    paid_via: PaidVia | Literal["unpaid"] = "unpaid"


class TeamUpdate(EditForm):
    NOT_NULL = frozenset({"name", "level_id"})

    name: TeamName | None = None
    level_id: UUID | None = None


class EntrantUpdate(EditForm):
    NOT_NULL = frozenset({"first_name", "last_name", "phone"})

    first_name: PersonName | None = None
    last_name: PersonName | None = None
    phone: Phone | None = None


class WithdrawIn(BaseModel):
    no_refund: bool = False
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""


class PlayerHit(BaseModel):
    """A player as the tournament admins may see them: enough to sign them
    up, nothing of the club's money."""

    player_id: UUID
    nickname: str
    avatar_url: str | None = None
    elo: int
    elo_level: str
    games: int
    line_linked: bool
    taken: bool


class Money(BaseModel):
    id: UUID
    tournament_id: UUID
    direction: Literal["income", "expense"]
    category: MoneyCategory
    category_other: str | None = None
    amount: float
    entry_date: date
    paid_by: UUID | None = None
    entrant_id: UUID | None = None
    team_id: UUID | None = None
    quantity: int | None = None
    unit_price: float | None = None
    paid_via: PaidVia | None = None
    receipt_url: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    # Written by the system from an entry (a fee received or refunded).
    automatic: bool = False


class MoneyIn(BaseModel):
    direction: Literal["income", "expense"]
    category: MoneyCategory
    category_other: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None
    ) = None
    amount: PositiveBaht
    entry_date: date
    paid_by: UUID | None = None
    paid_via: PaidVia | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None

    @model_validator(mode="after")
    def _manual(self) -> "MoneyIn":
        # Fees and refunds are written from the entries themselves.
        if self.category in {"entry_fee", "refund"}:
            raise ValueError("ค่าสมัครและการคืนค่าสมัครลงอัตโนมัติจากใบสมัคร")
        if self.category == "other" and not self.category_other:
            raise ValueError("หมวด อื่น ๆ ต้องบอกว่าเป็นอะไร")
        return self


class MoneySummary(BaseModel):
    income: float
    expense: float
    balance: float
    by_category: dict[str, float]
    by_level: dict[str, float]
    pending_slips: int
    pending_amount: float
    refunds_owed: int
    refunds_owed_amount: float


class AdminActivity(BaseModel):
    id: UUID
    admin_id: UUID
    admin_username: str
    action: str
    method: str
    path: str
    detail: dict[str, object] | None = None
    created_at: datetime


# --- phase 2: groups and the match list ---------------------------------------


class DrawTeam(BaseModel):
    id: UUID
    name: str
    status: TeamStatus
    group_label: str | None = None
    group_pos: int | None = None
    players: list[PublicPlayer]


class DrawLevel(BaseModel):
    level: Level
    confirmed: int
    not_ready: int
    """Teams holding or waiting for a place but not confirmed yet: not drawn."""
    groups: list[str]
    teams: list[DrawTeam]


class DrawState(BaseModel):
    tournament_id: UUID
    levels: list[DrawLevel]
    matches: list[Match]
    est_end: datetime | None = None
    published_at: datetime | None = None


class PlaceIn(BaseModel):
    group_label: Annotated[str, StringConstraints(pattern=r"^[A-H]$")]
    group_pos: Annotated[int, Field(ge=1, le=4)]


class PublishIn(BaseModel):
    on: bool
