from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

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


class JoinRequestAdmin(JoinApplication):
    """An application as the admin sees it, with who sent it on LINE."""

    line_name: str


class JoinApprove(BaseModel):
    elo_score: EloScore | None = None
    """Starting rating; the club default (1000) when omitted."""
