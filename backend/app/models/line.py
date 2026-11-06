from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.fields import EloScore, Handle, Note
from app.models.player import DominantHand, Player

LineUserId = Annotated[str, StringConstraints(pattern=r"^U[0-9a-f]{32}$")]


class LineContext(BaseModel):
    """A member signed in with LINE, from their token."""

    line_user_id: str
    line_name: str
    line_picture: str | None = None


class LineConfig(BaseModel):
    """What the /line page needs before it can start LIFF."""

    enabled: bool
    liff_id: str | None = None


class LineSessionIn(BaseModel):
    id_token: Annotated[str, StringConstraints(min_length=20, max_length=4096)]


class LinkRequest(BaseModel):
    """A member's pick, waiting for an admin."""

    id: UUID
    player: Player
    created_at: datetime


class JoinApplication(BaseModel):
    """A sign-up from someone not in the club yet, as they filled it in."""

    id: UUID
    nickname: str
    dominant_hand: DominantHand | None = None
    instagram: str | None = None
    tiktok: str | None = None
    quote: str | None = None
    photo_url: str | None = None
    created_at: datetime


class JoinIn(BaseModel):
    """The sign-up form. The nickname follows the club's rules
    (services/nickname_service.py), checked by the router."""

    nickname: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    dominant_hand: DominantHand | None = None
    instagram: Handle | None = None
    tiktok: Handle | None = None
    quote: Note | None = None
    use_line_photo: bool = True
    """No photo of their own: use their LINE picture."""


class LineStatus(BaseModel):
    """Who this LINE account is in the club, as far as it has got."""

    line_name: str
    line_picture: str | None = None
    player: Player | None = None
    """Set once an admin has approved the link."""
    pending: LinkRequest | None = None
    application: JoinApplication | None = None
    """A sign-up waiting for an admin (they are not in the club yet)."""
    token: str | None = None
    """Only on POST /api/line/session: what the page sends from then on."""


class LinkOption(BaseModel):
    """A name on the "who are you?" list."""

    id: UUID
    nickname: str
    member_code: str
    elo_level: str
    avatar_url: str | None = None
    games: int
    taken: bool
    """Already linked to a LINE account: shown, but can't be picked."""


class LinkPick(BaseModel):
    player_id: UUID


class LinkRequestAdmin(BaseModel):
    """A request as the admin sees it: who on LINE, claiming to be whom."""

    id: UUID
    line_name: str
    line_picture: str | None = None
    player: Player
    created_at: datetime


class LineLink(BaseModel):
    """A member whose LINE is linked, for the admin's list."""

    player_id: UUID
    line_name: str | None = None


class LineInvite(BaseModel):
    """The club's LINE link, as a QR the admin shows to members who haven't
    linked yet: it opens /line inside LINE, where they pick their name."""

    url: str
    qr_modules: list[str]
    """The QR as rows of 0/1, drawn as the club's QR card."""


class JoinRequestAdmin(JoinApplication):
    """An application as the admin sees it, with who sent it on LINE."""

    line_name: str


class JoinApprove(BaseModel):
    elo_score: EloScore | None = None
    """Starting rating; the club default (1000) when omitted."""


class CheckinNight(BaseModel):
    """The night a check-in QR is for."""

    id: UUID
    date: date
    location: str


class LineCheckinState(BaseModel):
    """What scanning tonight's QR leads to.

    ready: a linked member, not in yet. in: checked in (checkin_time set).
    expired: the code is not tonight's (closed night, old or replaced QR).
    unlinked: this LINE is nobody in the club yet."""

    state: Literal["ready", "in", "expired", "unlinked"]
    night: CheckinNight | None = None
    player: Player | None = None
    checkin_time: datetime | None = None


class LineCheckinIn(BaseModel):
    code: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{12,64}$")]


class GeoFix(BaseModel):
    """Where a phone says it is, and how sure it is (metres)."""

    model_config = ConfigDict(allow_inf_nan=False)

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0, le=100_000)


class LineGpsCheckin(BaseModel):
    """What checking in by location leads to.

    in: checked in (now, or already). far: not inside tonight's circle.
    none: no open night is pinned. weak: the phone is too unsure where it
    is. unlinked: this LINE is nobody in the club yet."""

    state: Literal["in", "far", "none", "weak", "unlinked"]
    night: CheckinNight | None = None
    player: Player | None = None
    checkin_time: datetime | None = None
    distance_m: int | None = None
    radius_m: int | None = None


class CheckinSpotIn(GeoFix):
    radius_m: int = Field(default=100, ge=30, le=500)


class CheckinSpot(BaseModel):
    """Tonight's pin, as the admin set it from their phone."""

    lat: float
    lng: float
    radius_m: int
    accuracy_m: int | None = None
    pinned_at: datetime | None = None


class CheckinQr(BaseModel):
    """Tonight's QR as the admin shows it at the court."""

    night: CheckinNight
    code: str
    url: str
    qr: str
    """A PNG data URI of `url`."""
    qr_modules: list[str]
    """The same QR as rows of 0/1, drawn as the club's QR card."""


class LineBill(BaseModel):
    """One of the member's own bills, as they see it."""

    id: UUID
    night: CheckinNight
    game_count: int
    amount: float
    """What they owe for it: the admin's adjustment if there is one."""
    paid_status: Literal["unpaid", "paid"]
    slip_url: str | None = None
    slip_sent_at: datetime | None = None
    slip_rejected_at: datetime | None = None
    credit_used: int = 0
    """How much of it club credit paid (services/bill_credit.py)."""
    left: float = 0
    """Still to transfer: amount less credit_used (0 once paid)."""


class LineBillCredit(BaseModel):
    """A bill just paid (all or part) with credit, and the balance left."""

    bill: LineBill
    balance: int


class LineTonight(BaseModel):
    """The member's night so far, for checking out.

    none: not checked in to an open night. in: checked in — `games` and
    `amount` are what checking out now would bill, `busy` that a match of
    theirs isn't finished yet. out: checked out, `bill` is the bill."""

    state: Literal["none", "in", "out"]
    night: CheckinNight | None = None
    player: Player | None = None
    games: int = 0
    court_fee: float = 0
    shuttle_price: float = 0
    amount: float = 0
    busy: bool = False
    bill: LineBill | None = None


class LineCheckoutIn(BaseModel):
    session_id: UUID


class LineBills(BaseModel):
    player: Player
    due: float
    """Unpaid and not waiting on a slip check."""
    bills: list[LineBill]
