"""Tonight's check-in QR: a LINE link carrying a code for one session.

The code is the only thing that ties a scan to a night, so it is random
(not the session id, which shows up in the admin's URLs) and it is only
honoured while that night is open and not more than a day old: a QR
photographed last week, or replaced because it leaked, checks nobody in.
"""

import secrets
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from supabase import Client

from app.config import get_settings
from app.db_utils import rows

CLUB_TZ = ZoneInfo("Asia/Bangkok")


def new_code() -> str:
    return secrets.token_urlsafe(12)


def checkin_url(code: str) -> str:
    """Opens the /line page inside LINE at /line/checkin (LIFF appends the
    path to the endpoint URL). A phone camera that scans it opens LINE."""
    return f"https://liff.line.me/{get_settings().line_liff_id}/checkin?c={code}"


def invite_url() -> str:
    """Opens the /line page inside LINE, where a member picks their name."""
    return f"https://liff.line.me/{get_settings().line_liff_id}"


def _today() -> date:
    return datetime.now(CLUB_TZ).date()


def is_current(night: dict[str, Any]) -> bool:
    """Open, and tonight — or last night, for a session that runs past
    midnight."""
    if night.get("status") != "open":
        return False
    return date.fromisoformat(str(night["date"])[:10]) >= _today() - timedelta(days=1)


def night_for(supabase: Client, code: str) -> dict[str, Any] | None:
    """The session this code checks people in to, if it still does."""
    found = rows(
        supabase.table("sessions").select("*").eq("line_checkin_code", code).limit(1).execute()
    )
    return found[0] if found and is_current(found[0]) else None
