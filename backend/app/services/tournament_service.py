"""NIDDEAW CUP sign-up (docs/tournament-spec.md, phase 1).

A team is two players. The captain signs up and invites a partner; the
partner accepts; each transfers their half to the tournament's own
PromptPay account and sends the slip. Both slips in and a place free, the
place is theirs ("slip_review") until a tournament admin checks the slips
("confirmed"). The level full, they wait in line ("waitlist") and move up
when a place frees.

    invited ──accept──▶ awaiting_payment ──both slips──▶ slip_review ──both paid──▶ confirmed
       │                     │                              │
       └─decline / runs out──┴──▶ cancelled                 └─slip refused, not resent in 24h──▶ cancelled
                                    (level full) ──▶ waitlist ──place frees──▶ slip_review

Nothing here touches the club's money: fees go to tournament_money, never
to billings, credit or other_income.

Timing that runs out (an invite unanswered, a slip not resent) is applied
lazily by `sweep`, called before every read — there is no background job.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows

TOURNAMENTS = "tournaments"
LEVELS = "tournament_levels"
TEAMS = "tournament_teams"
ENTRANTS = "tournament_entrants"
MONEY = "tournament_money"

SEATED = frozenset({"slip_review", "confirmed"})
"""Holding one of the level's places."""
LIVE = frozenset({"invited", "awaiting_payment", "slip_review", "confirmed", "waitlist"})
ENDED = frozenset({"cancelled", "withdrawn"})
PAID_OR_SENT = frozenset({"slip_sent", "paid"})

INVITE_HOURS = 48
PAY_HOURS = 48
RESEND_HOURS = 24

# The club's four levels (spec §1), the ELO tiers' own edges
# (elo_service._TIER_THRESHOLDS). Below Soju, no flick serve.
NO_FLICK = "ห้ามเสิร์ฟยิง"
DEFAULT_LEVELS: list[dict[str, Any]] = [
    {"name": "Milk–Beer", "min_elo": None, "max_elo": 1100, "rules": NO_FLICK},
    {"name": "Highball", "min_elo": 1100, "max_elo": 1300, "rules": NO_FLICK},
    {"name": "Wine", "min_elo": 1300, "max_elo": 1500, "rules": NO_FLICK},
    {"name": "Soju ขึ้นไป", "min_elo": 1500, "max_elo": None, "rules": ""},
]


def now() -> datetime:
    return datetime.now(UTC)


def when(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def refuse(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


# --- pure rules ---------------------------------------------------------------


def shares(tournament: dict[str, Any]) -> tuple[int, int]:
    """(captain, partner): each pays half of the entry and the first coupon
    set; the captain pays the odd baht."""
    total = int(tournament["entry_fee"]) + int(tournament["shuttle_fee"])
    return total - total // 2, total // 2


def in_level(elo: int, level: dict[str, Any]) -> bool:
    low, high = level.get("min_elo"), level.get("max_elo")
    return (low is None or elo >= int(low)) and (high is None or elo < int(high))


def sorted_levels(levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(levels, key=lambda lv: (int(lv.get("sort") or 0), str(lv["name"])))


def level_of(elo: int, levels: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The level a player's rating puts them in."""
    return next((lv for lv in sorted_levels(levels) if in_level(elo, lv)), None)


def allowed_levels(team_elo: int, levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Where a pair may play: the level of the stronger player, or any above.
    Never below — a pair can't drop a level to win (spec §1)."""
    return [
        lv
        for lv in sorted_levels(levels)
        if lv.get("max_elo") is None or team_elo < int(lv["max_elo"])
    ]


def taking_entries(tournament: dict[str, Any], at: datetime | None = None) -> bool:
    moment = at or now()
    opens = when(tournament.get("opens_at"))
    closes = when(tournament["closes_at"])
    return (
        tournament["status"] == "open"
        and (opens is None or moment >= opens)
        and closes is not None
        and moment < closes
    )


def games_needed(player: dict[str, Any], tournament: dict[str, Any]) -> int:
    return max(0, int(tournament["min_games"]) - int(player.get("games") or 0))


def refund_owed(team: dict[str, Any], entrant: dict[str, Any]) -> int:
    """Baht to give back to this player: their fee, received, for a team that
    did not play — unless an admin withdrew it keeping the fees."""
    if team["status"] not in ENDED or team.get("no_refund"):
        return 0
    return int(entrant["share"]) if entrant["pay_status"] == "paid" else 0


# --- reads ------------------------------------------------------------------


def tournament(supabase: Client, tournament_id: str) -> dict[str, Any]:
    found = rows(supabase.table(TOURNAMENTS).select("*").eq("id", tournament_id).limit(1).execute())
    if not found:
        raise refuse(status.HTTP_404_NOT_FOUND, "ไม่พบทัวร์นาเมนต์นี้")
    return found[0]


def current(supabase: Client) -> dict[str, Any] | None:
    """The tournament the public pages show: the latest one past its draft
    and not yet done."""
    found = rows(
        supabase.table(TOURNAMENTS)
        .select("*")
        .in_("status", ["open", "closed", "running"])
        .order("starts_on", desc=True)
        .limit(1)
        .execute()
    )
    return found[0] if found else None


def levels(supabase: Client, tournament_id: str) -> list[dict[str, Any]]:
    return sorted_levels(
        rows(supabase.table(LEVELS).select("*").eq("tournament_id", tournament_id).execute())
    )


def level(supabase: Client, tournament_id: str, level_id: str) -> dict[str, Any]:
    found = [lv for lv in levels(supabase, tournament_id) if str(lv["id"]) == str(level_id)]
    if not found:
        raise refuse(status.HTTP_404_NOT_FOUND, "ไม่พบมือนี้ในทัวร์นาเมนต์")
    return found[0]


def teams(supabase: Client, tournament_id: str) -> list[dict[str, Any]]:
    return rows(supabase.table(TEAMS).select("*").eq("tournament_id", tournament_id).execute())


def entrants(supabase: Client, tournament_id: str) -> list[dict[str, Any]]:
    return rows(supabase.table(ENTRANTS).select("*").eq("tournament_id", tournament_id).execute())


def team(supabase: Client, team_id: str) -> dict[str, Any]:
    found = rows(supabase.table(TEAMS).select("*").eq("id", team_id).limit(1).execute())
    if not found:
        raise refuse(status.HTTP_404_NOT_FOUND, "ไม่พบทีมนี้")
    return found[0]


def team_entrants(supabase: Client, team_id: str) -> list[dict[str, Any]]:
    found = rows(supabase.table(ENTRANTS).select("*").eq("team_id", team_id).execute())
    return sorted(found, key=lambda e: 0 if e["role"] == "captain" else 1)


def entrant(supabase: Client, entrant_id: str) -> dict[str, Any]:
    found = rows(supabase.table(ENTRANTS).select("*").eq("id", entrant_id).limit(1).execute())
    if not found:
        raise refuse(status.HTTP_404_NOT_FOUND, "ไม่พบผู้สมัครนี้")
    return found[0]


def active_entry(supabase: Client, tournament_id: str, player_id: str) -> dict[str, Any] | None:
    found = rows(
        supabase.table(ENTRANTS)
        .select("*")
        .eq("tournament_id", tournament_id)
        .eq("player_id", player_id)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    return found[0] if found else None


def players_by_id(supabase: Client, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    return {
        str(p["id"]): p
        for p in rows(supabase.table("players").select("*").in_("id", sorted(set(ids))).execute())
    }


def last_details(supabase: Client, player_id: str) -> dict[str, str] | None:
    """What this player typed last time, to fill the form in for them."""
    found = rows(
        supabase.table(ENTRANTS)
        .select("first_name,last_name,phone,created_at")
        .eq("player_id", player_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    for e in found:
        if e.get("first_name") and e.get("last_name") and e.get("phone"):
            return {"first_name": e["first_name"], "last_name": e["last_name"], "phone": e["phone"]}
    return None


def fees_locked(supabase: Client, tournament_id: str) -> bool:
    """True once anyone has sent a slip or paid: the price can't change after."""
    return any(
        e["pay_status"] != "unpaid" or e.get("slip_url") for e in entrants(supabase, tournament_id)
    )


# --- writes ----------------------------------------------------------------


def create_tournament(supabase: Client, payload: dict[str, Any], admin_id: str) -> dict[str, Any]:
    tid = str(uuid4())
    row = {
        "id": tid,
        "name": payload["name"],
        "starts_on": payload["starts_on"],
        "venue": payload.get("venue") or "",
        "entry_fee": 1600,
        "shuttle_fee": 450,
        "coupons_per_set": 6,
        "extra_set_price": 450,
        "coupon_refund_price": 70,
        "promptpay_id": None,
        "promptpay_type": None,
        "account_name": None,
        "opens_at": payload.get("opens_at"),
        "closes_at": payload["closes_at"],
        "min_games": 3,
        "courts": None,
        "status": "draft",
        "day_start": "09:00",
        "group_minutes": 20,
        "ko_minutes": 30,
        "rest_minutes": 10,
        "schedule_published_at": None,
        "created_by": admin_id,
        "created_at": iso(now()),
    }
    supabase.table(TOURNAMENTS).insert(row).execute()
    for i, lv in enumerate(DEFAULT_LEVELS):
        supabase.table(LEVELS).insert(
            {
                "id": str(uuid4()),
                "tournament_id": tid,
                "max_teams": 16,
                "cut_24": False,
                "sort": i,
                **lv,
            }
        ).execute()
    return tournament(supabase, tid)


def _set_team(supabase: Client, team_id: str, changes: dict[str, Any]) -> None:
    supabase.table(TEAMS).update(changes).eq("id", team_id).execute()


def _end(supabase: Client, team_row: dict[str, Any], to: str, no_refund: bool = False) -> None:
    """Cancel or withdraw a team: its two players are free to sign up again."""
    tid = str(team_row["id"])
    _set_team(
        supabase,
        tid,
        {"status": to, "ended_at": iso(now()), "expires_at": None, "no_refund": no_refund},
    )
    supabase.table(ENTRANTS).update({"active": False}).eq("team_id", tid).execute()
    team_row["status"] = to


def seats_taken(team_rows: list[dict[str, Any]], level_id: str) -> int:
    return sum(1 for t in team_rows if str(t["level_id"]) == level_id and t["status"] in SEATED)


def promote(supabase: Client, tournament_id: str, level_row: dict[str, Any]) -> None:
    """Fill free places in a level from its waiting line, first come first."""
    lid = str(level_row["id"])
    all_teams = teams(supabase, tournament_id)
    free = int(level_row["max_teams"]) - seats_taken(all_teams, lid)
    waiting = sorted(
        (t for t in all_teams if str(t["level_id"]) == lid and t["status"] == "waitlist"),
        key=lambda t: str(t.get("waitlist_at") or t.get("created_at") or ""),
    )
    for t in waiting[: max(0, free)]:
        _take_seat(supabase, t)


def _take_seat(supabase: Client, team_row: dict[str, Any]) -> None:
    ents = team_entrants(supabase, str(team_row["id"]))
    all_paid = all(e["pay_status"] == "paid" for e in ents)
    moment = iso(now())
    _set_team(
        supabase,
        str(team_row["id"]),
        {
            "status": "confirmed" if all_paid else "slip_review",
            "seat_held_at": moment,
            "confirmed_at": moment if all_paid else None,
            # Paid in full: the payment deadline no longer applies. A slip
            # refused later sets its own 24 hours (`reject`).
            "expires_at": None,
        },
    )


def settle(supabase: Client, team_id: str) -> None:
    """Move a team on after a payment changes: both slips in takes a place
    (or a place in line); both paid confirms it."""
    t = team(supabase, team_id)
    ents = team_entrants(supabase, team_id)
    if t["status"] not in LIVE or len(ents) < 2:
        return
    any_refused = any(e["pay_status"] == "rejected" for e in ents)
    all_in = all(e["pay_status"] in PAID_OR_SENT for e in ents)
    all_paid = all(e["pay_status"] == "paid" for e in ents)

    if t["status"] == "awaiting_payment" and all_in:
        lv = level(supabase, str(t["tournament_id"]), str(t["level_id"]))
        if seats_taken(teams(supabase, str(t["tournament_id"])), str(t["level_id"])) < int(
            lv["max_teams"]
        ):
            _take_seat(supabase, t)
        else:
            _set_team(
                supabase,
                team_id,
                {"status": "waitlist", "waitlist_at": iso(now()), "expires_at": None},
            )
        return
    if t["status"] == "slip_review" and all_paid:
        _set_team(
            supabase,
            team_id,
            {"status": "confirmed", "confirmed_at": iso(now()), "expires_at": None},
        )
        return
    if t["status"] in {"slip_review", "waitlist"} and not any_refused and t.get("expires_at"):
        # A refused slip was sent again: the 24 hours no longer apply.
        _set_team(supabase, team_id, {"expires_at": None})
    if t["status"] == "confirmed" and not all_paid:
        # A payment taken back (an admin's mistake undone): back to checking.
        _set_team(supabase, team_id, {"status": "slip_review", "confirmed_at": None})


def sweep(
    supabase: Client,
    tournament_id: str,
    found_teams: list[dict[str, Any]] | None = None,
    found_levels: list[dict[str, Any]] | None = None,
) -> bool:
    """End what has run out — an invite unanswered, a payment not made, a
    refused slip not resent — and fill the places that frees.

    Every page of the tournament runs this on the way in, so the usual case
    — nothing has run out, nobody can move up — costs at most the one read,
    or none when the caller already holds the teams and levels. Returns
    whether anything changed, so a caller holding rows knows to read again."""
    moment = now()
    all_teams = found_teams if found_teams is not None else teams(supabase, tournament_id)
    changed = False
    for t in all_teams:
        expires = when(t.get("expires_at"))
        if (
            t["status"] in LIVE
            and t["status"] != "confirmed"
            and expires is not None
            and expires <= moment
        ):
            _end(supabase, t, "cancelled")
            changed = True
    if not any(t["status"] == "waitlist" for t in all_teams):
        return changed
    if changed:
        all_teams = teams(supabase, tournament_id)
    for lv in found_levels if found_levels is not None else levels(supabase, tournament_id):
        lid = str(lv["id"])
        free = int(lv["max_teams"]) - seats_taken(all_teams, lid)
        if free > 0 and any(
            t["status"] == "waitlist" and str(t["level_id"]) == lid for t in all_teams
        ):
            promote(supabase, tournament_id, lv)
            changed = True
    return changed


def _deadline(tournament_row: dict[str, Any], hours: int) -> str:
    closes = when(tournament_row["closes_at"])
    limit = now() + timedelta(hours=hours)
    return iso(min(limit, closes) if closes else limit)


@dataclass
class Pair:
    captain: dict[str, Any]
    partner: dict[str, Any]


def check_pair(
    supabase: Client, tournament_row: dict[str, Any], pair: Pair, level_id: str, line_needed: bool
) -> dict[str, Any]:
    """Everything that must hold for these two to sign up in this level.
    Returns the level."""
    tid = str(tournament_row["id"])
    a, b = pair.captain, pair.partner
    if str(a["id"]) == str(b["id"]):
        raise refuse(status.HTTP_400_BAD_REQUEST, "เลือกคู่เป็นตัวเองไม่ได้")
    for p in (a, b):
        if not p.get("is_active", True):
            raise refuse(status.HTTP_400_BAD_REQUEST, f"{p['nickname']} ไม่ได้อยู่ในรายชื่อแล้ว")
        need = games_needed(p, tournament_row)
        if need:
            raise refuse(
                status.HTTP_400_BAD_REQUEST,
                f"{p['nickname']} ต้องตีที่ก๊วนอีก {need} เกมก่อนถึงจะสมัครได้",
            )
        if active_entry(supabase, tid, str(p["id"])):
            raise refuse(status.HTTP_409_CONFLICT, f"{p['nickname']} อยู่ในทีมอื่นของงานนี้แล้ว")
    if line_needed and not b.get("line_user_id"):
        raise refuse(
            status.HTTP_400_BAD_REQUEST,
            f"{b['nickname']} ยังไม่ได้ผูก LINE — ให้ผูก LINE ก่อน หรือให้แอดมินสมัครแทน",
        )
    lv = level(supabase, tid, level_id)
    team_elo = max(int(a.get("elo_score") or 0), int(b.get("elo_score") or 0))
    if str(lv["id"]) not in {str(x["id"]) for x in allowed_levels(team_elo, levels(supabase, tid))}:
        raise refuse(
            status.HTTP_400_BAD_REQUEST,
            f"คู่นี้ลงมือ {lv['name']} ไม่ได้ — ลงได้แค่มือของคนที่เก่งกว่า หรือมือที่สูงกว่า",
        )
    return lv


def create_team(
    supabase: Client,
    tournament_row: dict[str, Any],
    level_id: str,
    name: str,
    captain: tuple[dict[str, Any], dict[str, str]],
    partner: tuple[dict[str, Any], dict[str, str] | None],
    admin_id: str | None = None,
) -> str:
    """Write a team and its two entrants. From LINE the partner's details
    come when they accept; an admin signing a pair up gives both."""
    tid = str(tournament_row["id"])
    cap_share, partner_share = shares(tournament_row)
    team_id = str(uuid4())
    moment = now()
    accepted = partner[1] is not None
    supabase.table(TEAMS).insert(
        {
            "id": team_id,
            "tournament_id": tid,
            "level_id": level_id,
            "name": name.strip(),
            "status": "awaiting_payment" if accepted else "invited",
            "expires_at": None
            if admin_id
            else _deadline(tournament_row, PAY_HOURS if accepted else INVITE_HOURS),
            "invited_at": iso(moment),
            "accepted_at": iso(moment) if accepted else None,
            "seat_held_at": None,
            "waitlist_at": None,
            "confirmed_at": None,
            "ended_at": None,
            "no_refund": False,
            "created_by_admin": admin_id,
            "created_at": iso(moment),
        }
    ).execute()
    for role, (player, details), share in (
        ("captain", captain, cap_share),
        ("partner", partner, partner_share),
    ):
        supabase.table(ENTRANTS).insert(
            {
                "id": str(uuid4()),
                "tournament_id": tid,
                "team_id": team_id,
                "player_id": str(player["id"]),
                "role": role,
                "active": True,
                "first_name": details["first_name"] if details else None,
                "last_name": details["last_name"] if details else None,
                "phone": details["phone"] if details else None,
                "elo": int(player.get("elo_score") or 0),
                "share": share,
                "pay_status": "unpaid",
                "paid_via": None,
                "slip_url": None,
                "slip_sent_at": None,
                "paid_at": None,
                "checked_by": None,
                "rejected_at": None,
                "refund_slip_url": None,
                "refunded_at": None,
                "created_at": iso(moment),
            }
        ).execute()
    return team_id


def accept(
    supabase: Client, tournament_row: dict[str, Any], entry: dict[str, Any], details: dict[str, str]
) -> None:
    t = team(supabase, str(entry["team_id"]))
    if entry["role"] != "partner" or t["status"] != "invited":
        raise refuse(status.HTTP_409_CONFLICT, "ไม่มีคำชวนที่รอตอบอยู่")
    supabase.table(ENTRANTS).update(details).eq("id", str(entry["id"])).execute()
    _set_team(
        supabase,
        str(t["id"]),
        {
            "status": "awaiting_payment",
            "accepted_at": iso(now()),
            "expires_at": _deadline(tournament_row, PAY_HOURS),
        },
    )


def record_slip(supabase: Client, entry: dict[str, Any], url: str) -> None:
    """A player's slip for their half. Sending again replaces the last one."""
    t = team(supabase, str(entry["team_id"]))
    if t["status"] not in LIVE or t["status"] == "invited":
        raise refuse(status.HTTP_409_CONFLICT, "ทีมนี้ยังไม่ถึงขั้นโอน หรือจบไปแล้ว")
    if entry["pay_status"] == "paid":
        raise refuse(status.HTTP_409_CONFLICT, "แอดมินตรวจยอดของคุณแล้ว ไม่ต้องส่งสลิปอีก")
    supabase.table(ENTRANTS).update(
        {
            "slip_url": url,
            "slip_sent_at": iso(now()),
            "pay_status": "slip_sent",
            "paid_via": "transfer",
            "rejected_at": None,
        }
    ).eq("id", str(entry["id"])).execute()
    settle(supabase, str(t["id"]))


def _fee_row(supabase: Client, entry: dict[str, Any], admin_id: str, via: str) -> None:
    existing = rows(
        supabase.table(MONEY)
        .select("id")
        .eq("entrant_id", str(entry["id"]))
        .eq("category", "entry_fee")
        .execute()
    )
    if existing:
        return
    supabase.table(MONEY).insert(
        {
            "id": str(uuid4()),
            "tournament_id": str(entry["tournament_id"]),
            "direction": "income",
            "category": "entry_fee",
            "category_other": None,
            "amount": int(entry["share"]),
            "entry_date": now().date().isoformat(),
            "paid_by": None,
            "entrant_id": str(entry["id"]),
            "team_id": str(entry["team_id"]),
            "quantity": None,
            "unit_price": None,
            "paid_via": via,
            "receipt_url": entry.get("slip_url"),
            "note": None,
            "created_by": admin_id,
            "created_at": iso(now()),
        }
    ).execute()


def mark_paid(supabase: Client, entry: dict[str, Any], admin_id: str, via: str) -> None:
    """A slip checked and the money in (or cash taken at the desk): it now
    counts as the tournament's income."""
    if entry["pay_status"] in {"paid", "refunded"}:
        raise refuse(status.HTTP_409_CONFLICT, "รายการนี้ตรวจไปแล้ว")
    if via == "transfer" and entry["pay_status"] != "slip_sent":
        raise refuse(status.HTTP_409_CONFLICT, "ยังไม่มีสลิปให้ตรวจ")
    supabase.table(ENTRANTS).update(
        {
            "pay_status": "paid",
            "paid_via": via,
            "paid_at": iso(now()),
            "checked_by": admin_id,
            "rejected_at": None,
        }
    ).eq("id", str(entry["id"])).execute()
    _fee_row(supabase, {**entry, "pay_status": "paid"}, admin_id, via)
    settle(supabase, str(entry["team_id"]))


def reject(supabase: Client, entry: dict[str, Any], admin_id: str) -> None:
    """A slip that doesn't hold up. The player has 24 hours to send another
    before a held place is given up."""
    if entry["pay_status"] != "slip_sent":
        raise refuse(status.HTTP_409_CONFLICT, "ไม่มีสลิปที่รอตรวจ")
    supabase.table(ENTRANTS).update(
        {"pay_status": "rejected", "rejected_at": iso(now()), "checked_by": admin_id}
    ).eq("id", str(entry["id"])).execute()
    t = team(supabase, str(entry["team_id"]))
    if t["status"] in {"slip_review", "waitlist"}:
        _set_team(
            supabase, str(t["id"]), {"expires_at": iso(now() + timedelta(hours=RESEND_HOURS))}
        )


def end_team(supabase: Client, team_row: dict[str, Any], to: str, no_refund: bool = False) -> None:
    was_seated = team_row["status"] in SEATED
    _end(supabase, team_row, to, no_refund)
    if was_seated:
        promote(
            supabase,
            str(team_row["tournament_id"]),
            level(supabase, str(team_row["tournament_id"]), str(team_row["level_id"])),
        )


def refund(supabase: Client, entry: dict[str, Any], admin_id: str, slip_url: str | None) -> None:
    t = team(supabase, str(entry["team_id"]))
    owed = refund_owed(t, entry)
    if not owed:
        raise refuse(status.HTTP_409_CONFLICT, "ไม่มียอดต้องคืนให้คนนี้")
    supabase.table(ENTRANTS).update(
        {"pay_status": "refunded", "refunded_at": iso(now()), "refund_slip_url": slip_url}
    ).eq("id", str(entry["id"])).execute()
    supabase.table(MONEY).insert(
        {
            "id": str(uuid4()),
            "tournament_id": str(entry["tournament_id"]),
            "direction": "expense",
            "category": "refund",
            "category_other": None,
            "amount": owed,
            "entry_date": now().date().isoformat(),
            "paid_by": admin_id,
            "entrant_id": str(entry["id"]),
            "team_id": str(entry["team_id"]),
            "quantity": None,
            "unit_price": None,
            "paid_via": "transfer" if slip_url else None,
            "receipt_url": slip_url,
            "note": None,
            "created_by": admin_id,
            "created_at": iso(now()),
        }
    ).execute()


def resize_level(supabase: Client, tournament_id: str, level_row: dict[str, Any]) -> None:
    """After a level's size changes: the last teams to take a place go to the
    front of the waiting line if it shrank, the line moves up if it grew."""
    lid = str(level_row["id"])
    seated = sorted(
        (
            t
            for t in teams(supabase, tournament_id)
            if str(t["level_id"]) == lid and t["status"] in SEATED
        ),
        key=lambda t: str(t.get("seat_held_at") or ""),
    )
    for t in seated[int(level_row["max_teams"]) :]:
        _set_team(
            supabase,
            str(t["id"]),
            {
                "status": "waitlist",
                "waitlist_at": t.get("seat_held_at"),
                "seat_held_at": None,
                "confirmed_at": None,
            },
        )
    promote(supabase, tournament_id, level_row)
