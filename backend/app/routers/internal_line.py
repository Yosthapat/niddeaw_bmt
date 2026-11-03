"""What the Friday GitHub Action knocks on to send the check-in reminder
(app/services/line_reminder.py). Guarded by its own shared secret, like the
weekly Sheets sync: unset, the endpoint does not exist."""

from __future__ import annotations

import hmac
from typing import Annotated

import httpx
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.deps import SupabaseDep
from app.services import line_reminder

router = APIRouter(prefix="/api/internal", tags=["internal"])


class ReminderDone(BaseModel):
    sent: int
    reason: str


@router.post("/line-checkin-reminder", response_model=ReminderDone)
def checkin_reminder(
    supabase: SupabaseDep,
    x_reminder_secret: Annotated[str | None, Header()] = None,
) -> ReminderDone:
    secret = get_settings().line_reminder_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if x_reminder_secret is None or not hmac.compare_digest(x_reminder_secret.encode(), secret.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        done = line_reminder.send(supabase)
    except httpx.HTTPError as exc:
        # LINE refused or didn't answer: a 502 fails the Action, so the
        # owner hears about it, and the night stays unclaimed for a retry.
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LINE did not accept the reminder") from exc
    return ReminderDone(sent=done.sent, reason=done.reason)
