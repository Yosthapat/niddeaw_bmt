import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.fields import Name


def normalise_link(raw: str | None) -> str | None:
    """What an admin types into "Instagram or website", as a URL.

    Sponsors are mostly Instagram accounts, and the handle is what people
    have to hand: "@match.mellowww" and "instagram.com/match.mellowww" both
    become the full link. Anything else must already be a web address.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    handle = re.fullmatch(r"@?([A-Za-z0-9._]{1,30})", text)
    if handle and (text.startswith("@") or "." not in text):
        return f"https://www.instagram.com/{handle.group(1)}"
    if not re.match(r"^https?://", text):
        text = "https://" + text
    if not re.match(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$", text):
        raise ValueError("ลิงก์ต้องเป็น @ชื่อ Instagram หรือเว็บไซต์")
    if len(text) > 300:
        raise ValueError("ลิงก์ยาวเกินไป")
    return text


class SponsorUpdate(BaseModel):
    name: Name | None = None
    href: str | None = None
    """Run through normalise_link by the router, which turns a bad one
    into a 400 with the reason rather than a bare 422."""
    is_visible: bool | None = None


class SponsorOrder(BaseModel):
    ids: list[UUID]


class Sponsor(BaseModel):
    id: UUID
    name: str
    href: str | None = None
    logo_url: str
    logo_width: int
    logo_height: int
    sort_order: int
    is_visible: bool
    created_at: datetime


class LogoPreview(BaseModel):
    data_uri: str
    width: int
    height: int
