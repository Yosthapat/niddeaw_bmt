"""The Friday-evening nudge to check in, sent through the club's LINE OA.

A scheduled GitHub Action knocks at 19:30, 20:00 and 20:30 Bangkok time
(.github/workflows/line-checkin-reminder.yml). The first knock that finds
tonight's night open sends it; the night remembers that it did
(sessions.line_reminder_sent_at), so the later knocks send nothing. A night
the admin opens after 20:30 gets no reminder.

Who gets it: members who linked their LINE, are active, have not checked in
to tonight's night, and checked in to at least one of the last
RECENT_NIGHTS nights. That keeps it to the people likely to be on the way,
not everyone who ever linked.

Every message is one of the OA's monthly messages per person (300 on the
free plan, and the free plan cannot buy more). So the OA's remaining quota
is read first, and the list is cut to what is left, most recent players
first. Nothing is sent when nothing is left.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx
from supabase import Client

from app.config import get_settings
from app.db_utils import rows
from app.services.line_checkin import CLUB_TZ

RECENT_NIGHTS = 4
API = "https://api.line.me/v2/bot"
MULTICAST_MAX = 500  # LINE's cap on recipients per multicast call


def message_text() -> str:
    liff = get_settings().line_liff_id
    link = f"\nhttps://liff.line.me/{liff}/checkin" if liff else ""
    return (
        "🏸 ถึงสนามแล้วอย่าลืมเช็คอินนะ!\n"
        'กด "ผูกชื่อ เช็คอิน" ที่เมนูด้านล่าง แล้วสแกน QR ที่โต๊ะแอดมิน 📲\n'
        "เช็คอินแล้วได้เข้าคิวจัดคู่ ลงสนามไวขึ้น 🐱👑" + link
    )


@dataclass
class Outcome:
    sent: int
    reason: str  # "sent" or why nothing (more) went out


def _today() -> date:
    return datetime.now(CLUB_TZ).date()


def tonight(supabase: Client) -> dict[str, Any] | None:
    """Tonight's open night, if the admin has opened it."""
    today = _today().isoformat()
    found = rows(supabase.table("sessions").select("*").eq("date", today).eq("status", "open").execute())
    found = [s for s in found if str(s.get("date"))[:10] == today and s.get("status") == "open"]
    return found[0] if found else None


def recipients(supabase: Client, night: dict[str, Any]) -> list[str]:
    """LINE user ids to remind, most recent player first."""
    earlier = rows(
        supabase.table("sessions")
        .select("id, date")
        .lt("date", str(night["date"])[:10])
        .order("date", desc=True)
        .limit(RECENT_NIGHTS)
        .execute()
    )
    earlier = sorted(
        (s for s in earlier if str(s["date"])[:10] < str(night["date"])[:10]),
        key=lambda s: str(s["date"]),
        reverse=True,
    )[:RECENT_NIGHTS]
    if not earlier:
        return []
    order = {str(s["id"]): i for i, s in enumerate(earlier)}
    ids = [*order, str(night["id"])]
    checkins = rows(supabase.table("checkins").select("session_id, player_id").in_("session_id", ids).execute())
    here = {str(c["player_id"]) for c in checkins if str(c["session_id"]) == str(night["id"])}
    last_seen: dict[str, int] = {}
    for c in checkins:
        at = order.get(str(c["session_id"]))
        if at is not None:
            pid = str(c["player_id"])
            last_seen[pid] = min(at, last_seen.get(pid, at))
    wanted = [pid for pid in last_seen if pid not in here]
    if not wanted:
        return []
    players = rows(
        supabase.table("players").select("id, line_user_id, is_active").in_("id", wanted).execute()
    )
    keep = set(wanted)
    linked = [p for p in players if p.get("line_user_id") and p.get("is_active") and str(p["id"]) in keep]
    linked.sort(key=lambda p: (last_seen[str(p["id"])], str(p["id"])))
    return [str(p["line_user_id"]) for p in linked]


def remaining_quota(http: httpx.Client, token: str) -> int | None:
    """Messages the OA can still send this month; None when unlimited."""
    auth = {"Authorization": f"Bearer {token}"}
    quota = http.get(f"{API}/message/quota", headers=auth)
    quota.raise_for_status()
    body = quota.json()
    if body.get("type") != "limited":
        return None
    used = http.get(f"{API}/message/quota/consumption", headers=auth)
    used.raise_for_status()
    return max(0, int(body.get("value", 0)) - int(used.json().get("totalUsage", 0)))


def send(supabase: Client, http: httpx.Client | None = None) -> Outcome:
    token = get_settings().line_messaging_token
    if not token:
        return Outcome(0, "not set up: LINE_MESSAGING_TOKEN is missing")
    night = tonight(supabase)
    if not night:
        return Outcome(0, "no open night today")
    if night.get("line_reminder_sent_at"):
        return Outcome(0, "already sent tonight")

    # Claim the night before sending, so two knocks at once can't both send.
    stamp = datetime.now(UTC).isoformat()
    claimed = rows(
        supabase.table("sessions")
        .update({"line_reminder_sent_at": stamp, "line_reminder_count": 0})
        .eq("id", str(night["id"]))
        .is_("line_reminder_sent_at", "null")
        .execute()
    )
    if not claimed:
        return Outcome(0, "already sent tonight")

    def release() -> None:
        supabase.table("sessions").update({"line_reminder_sent_at": None, "line_reminder_count": None}).eq(
            "id", str(night["id"])
        ).execute()

    client = http or httpx.Client(timeout=15)
    sent = 0
    try:
        to = recipients(supabase, night)
        if not to:
            return Outcome(0, "nobody to remind")
        left = remaining_quota(client, token)
        if left is not None:
            to = to[:left]
        if not to:
            release()  # nothing went out: a later knock may try again
            return Outcome(0, "no messages left in this month's LINE quota")
        message = [{"type": "text", "text": message_text()}]
        for i in range(0, len(to), MULTICAST_MAX):
            batch = to[i : i + MULTICAST_MAX]
            res = client.post(
                f"{API}/message/multicast",
                headers={"Authorization": f"Bearer {token}"},
                json={"to": batch, "messages": message},
            )
            res.raise_for_status()
            sent += len(batch)
    except httpx.HTTPError:
        if sent:
            supabase.table("sessions").update({"line_reminder_count": sent}).eq("id", str(night["id"])).execute()
        else:
            release()  # nothing went out: let the next knock retry
        raise
    finally:
        if http is None:
            client.close()
    supabase.table("sessions").update({"line_reminder_count": sent}).eq("id", str(night["id"])).execute()
    return Outcome(sent, "sent")
