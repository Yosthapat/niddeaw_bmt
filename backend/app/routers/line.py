"""The /line page: a member opens it inside LINE (LIFF) and links their LINE
account to their name in the club.

POST /session trades LINE's ID token for one of ours, after LINE itself
has vouched for it (services/line_auth.py). Everything else here takes that
token. A link is only ever requested here; an admin approves it
(routers/admin/line_admin.py), since otherwise anyone could claim anyone.
"""

import re
from collections import deque
from datetime import UTC, date, datetime
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from supabase import Client

from app.config import get_settings
from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import (
    CheckinNight,
    GeoFix,
    JoinApplication,
    JoinIn,
    LineBill,
    LineBillCredit,
    LineBills,
    LineCheckinIn,
    LineCheckinState,
    LineCheckoutIn,
    LineConfig,
    LineContext,
    LineGpsCheckin,
    LineSessionIn,
    LineStatus,
    LineTonight,
    LinkOption,
    LinkPick,
    LinkRequest,
)
from app.models.payment import PaymentInfoResponse
from app.models.player import Player
from app.routers.admin.players_admin import check_nickname
from app.security import create_line_token
from app.services import (
    bill_credit,
    billing_service,
    checkin_service,
    credit_service,
    line_auth,
    line_checkin,
    line_gps,
    line_join,
    login_throttle,
    nickname_service,
    night_bill,
    payment_info_service,
)
from app.services.image_service import resize_jpeg

router = APIRouter(prefix="/api/line", tags=["line"])

TABLE = "line_link_requests"
JOINS = "line_join_requests"
CODE = re.compile(r"[A-Za-z0-9_-]{12,64}")


def _player(supabase: Client, player_id: str) -> dict[str, Any] | None:
    found = rows(supabase.table("players").select("*").eq("id", player_id).limit(1).execute())
    return found[0] if found else None


def _pending(supabase: Client, line_user_id: str) -> dict[str, Any] | None:
    found = rows(
        supabase.table(TABLE)
        .select("*")
        .eq("line_user_id", line_user_id)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    return found[0] if found else None


def _pending_join(supabase: Client, line_user_id: str) -> dict[str, Any] | None:
    found = rows(
        supabase.table(JOINS)
        .select("*")
        .eq("line_user_id", line_user_id)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    return found[0] if found else None


def status_of(
    supabase: Client, line_user_id: str, line_name: str, picture: str | None = None
) -> LineStatus:
    linked = rows(
        supabase.table("players").select("*").eq("line_user_id", line_user_id).limit(1).execute()
    )
    if linked:
        return LineStatus(
            line_name=line_name, line_picture=picture, player=Player.model_validate(linked[0])
        )
    pending = _pending(supabase, line_user_id)
    claimed = _player(supabase, str(pending["player_id"])) if pending else None
    joining = _pending_join(supabase, line_user_id)
    return LineStatus(
        line_name=line_name,
        line_picture=picture or (pending or {}).get("line_picture"),
        application=JoinApplication.model_validate(joining) if joining else None,
        pending=LinkRequest(
            id=pending["id"],
            player=Player.model_validate(claimed),
            created_at=pending["created_at"],
        )
        if pending and claimed
        else None,
    )


@router.get("/config", response_model=LineConfig)
def config() -> LineConfig:
    settings = get_settings()
    return LineConfig(enabled=line_auth.configured(), liff_id=settings.line_liff_id)


# Each sign-in asks LINE to check the token (an outbound call that can take
# seconds), so a flood of them would tie up the server. Generous, because
# everyone on the court's wifi shares one address and opens the page a few
# times a night.
SESSIONS_PER_WINDOW = 120
SESSION_WINDOW_SECONDS = 10 * 60
_recent_sessions: dict[str, deque[float]] = {}


def _throttle_sessions(request: Request) -> None:
    key = login_throttle.client_key(
        request.headers.get("x-forwarded-for"), request.client.host if request.client else None
    )
    now = monotonic()
    stamps = _recent_sessions.setdefault(key, deque())
    while stamps and now - stamps[0] >= SESSION_WINDOW_SECONDS:
        stamps.popleft()
    if len(stamps) >= SESSIONS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="เข้าสู่ระบบบ่อยเกินไป ลองใหม่อีกครั้งในอีกสักพัก",
        )
    stamps.append(now)


def reset_throttle() -> None:
    _recent_sessions.clear()


@router.post("/session", response_model=LineStatus)
def start_session(payload: LineSessionIn, request: Request, supabase: SupabaseDep) -> LineStatus:
    _throttle_sessions(request)
    if not line_auth.configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ยังไม่ได้ตั้งค่า LINE"
        )
    try:
        profile = line_auth.verify_id_token(payload.id_token)
    except line_auth.LineAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="LINE ยืนยันตัวตนไม่ผ่าน — ปิดแล้วเปิดใหม่อีกครั้ง"
        ) from exc
    found = status_of(supabase, profile.user_id, profile.name, profile.picture)
    found.token = create_line_token(profile.user_id, profile.name, profile.picture)
    return found


@router.get("/me", response_model=LineStatus)
def me(supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    return status_of(supabase, member.line_user_id, member.line_name, member.line_picture)


@router.get("/link/options", response_model=list[LinkOption])
def link_options(supabase: SupabaseDep, member: LineMemberDep) -> list[LinkOption]:
    """Every active member, those already linked marked as taken."""
    players = rows(
        supabase.table("players").select("*").eq("is_active", True).order("nickname").execute()
    )
    return [
        LinkOption(
            id=p["id"],
            nickname=p["nickname"],
            member_code=f"ND{int(p['member_seq']):03d}",
            elo_level=p["elo_level"],
            avatar_url=p.get("avatar_url"),
            games=int(p.get("games") or 0),
            taken=bool(p.get("line_user_id")),
        )
        for p in players
        if p.get("is_active", True)
    ]


@router.post("/link", response_model=LineStatus)
def request_link(payload: LinkPick, supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    """File "this LINE is me" for an admin to approve. Picking again
    replaces the earlier pick."""
    now = status_of(supabase, member.line_user_id, member.line_name)
    if now.player is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"LINE นี้ผูกกับ {now.player.nickname} แล้ว — ถ้าผิด บอกแอดมินให้ยกเลิกก่อน",
        )
    player = _player(supabase, str(payload.player_id))
    if player is None or not player.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบสมาชิกคนนี้")
    if player.get("line_user_id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{player['nickname']} ผูก LINE ไว้แล้ว — ถ้าเป็นชื่อคุณจริง บอกแอดมินที่สนาม",
        )
    supabase.table(TABLE).delete().eq("line_user_id", member.line_user_id).eq(
        "status", "pending"
    ).execute()
    # Picking a name means they are in the club after all: any sign-up
    # they sent is withdrawn.
    _withdraw_join(supabase, member.line_user_id)
    supabase.table(TABLE).insert(
        {
            "line_user_id": member.line_user_id,
            "line_name": member.line_name[:100] or "LINE",
            "line_picture": member.line_picture,
            "player_id": str(payload.player_id),
            "status": "pending",
        }
    ).execute()
    return status_of(supabase, member.line_user_id, member.line_name)


@router.delete("/link", response_model=LineStatus)
def cancel_link(supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    """Picked the wrong name: withdraw the request to pick again."""
    supabase.table(TABLE).delete().eq("line_user_id", member.line_user_id).eq(
        "status", "pending"
    ).execute()
    return status_of(supabase, member.line_user_id, member.line_name)


def _withdraw_join(supabase: Client, line_user_id: str) -> None:
    joining = _pending_join(supabase, line_user_id)
    if joining:
        supabase.table(JOINS).delete().eq("id", str(joining["id"])).execute()
        line_join.remove_photo(supabase, joining.get("photo_url"))


def _not_yet_a_member(supabase: Client, member: LineContext) -> None:
    linked = rows(
        supabase.table("players")
        .select("nickname")
        .eq("line_user_id", member.line_user_id)
        .execute()
    )
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"LINE นี้เป็นสมาชิก {linked[0]['nickname']} อยู่แล้ว",
        )


@router.post("/join", response_model=LineStatus)
def join(payload: JoinIn, supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    """Send (or resend) a sign-up. Nobody is in the club until an admin
    accepts it (routers/admin/line_admin.py)."""
    _not_yet_a_member(supabase, member)
    # A capital then small letters, whatever they typed ("VAAN" → "Vaan").
    nickname = check_nickname(supabase, nickname_service.tidy_case(payload.nickname))
    # Two people waiting with the same name would leave the admin to turn
    # one down for it later; tell the second one now. The format rule has
    # already ruled out % and _, so ilike can only match the name itself.
    clash = rows(
        supabase.table(JOINS)
        .select("line_user_id")
        .eq("status", "pending")
        .ilike("nickname", nickname)
        .execute()
    )
    if any(r["line_user_id"] != member.line_user_id for r in clash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'มีคนสมัครด้วยชื่อ "{nickname}" รออยู่แล้ว — ลองชื่ออื่น',
        )
    fields: dict[str, Any] = {
        "line_name": member.line_name[:100] or "LINE",
        "nickname": nickname,
        "dominant_hand": payload.dominant_hand,
        "instagram": payload.instagram or None,
        "tiktok": payload.tiktok or None,
        "quote": payload.quote or None,
    }
    before = _pending_join(supabase, member.line_user_id)
    if payload.use_line_photo:
        picture = line_join.fetch_line_picture(member.line_picture or "")
        try:
            fields["photo_url"] = (
                line_join.store_photo(supabase, member.line_user_id[1:9], picture)
                if picture
                else None
            )
        except ValueError:
            fields["photo_url"] = None
        if before and before.get("photo_url") != fields["photo_url"]:
            line_join.remove_photo(supabase, before.get("photo_url"))
    if before:
        supabase.table(JOINS).update(fields).eq("id", str(before["id"])).execute()
    else:
        # They are signing up rather than claiming a name: drop any claim.
        supabase.table(TABLE).delete().eq("line_user_id", member.line_user_id).eq(
            "status", "pending"
        ).execute()
        supabase.table(JOINS).insert(
            {**fields, "line_user_id": member.line_user_id, "status": "pending"}
        ).execute()
    return status_of(supabase, member.line_user_id, member.line_name, member.line_picture)


@router.post("/join/photo", response_model=LineStatus)
async def join_photo(file: UploadFile, supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    """Their own photo for the sign-up they already sent."""
    joining = _pending_join(supabase, member.line_user_id)
    if joining is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ยังไม่ได้ส่งใบสมัคร")
    contents = await file.read(
        line_join.MAX_PHOTO_BYTES + 1
    )  # never more than one byte past the limit
    if len(contents) > line_join.MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="รูปใหญ่เกินไป (ไม่เกิน 2MB)"
        )
    try:
        url = line_join.store_photo(supabase, member.line_user_id[1:9], contents)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์นี้ไม่ใช่รูปภาพ"
        ) from None
    supabase.table(JOINS).update({"photo_url": url}).eq("id", str(joining["id"])).execute()
    if joining.get("photo_url") != url:
        line_join.remove_photo(supabase, joining.get("photo_url"))
    return status_of(supabase, member.line_user_id, member.line_name, member.line_picture)


@router.delete("/join", response_model=LineStatus)
def cancel_join(supabase: SupabaseDep, member: LineMemberDep) -> LineStatus:
    _withdraw_join(supabase, member.line_user_id)
    return status_of(supabase, member.line_user_id, member.line_name, member.line_picture)


# --- checking in by scanning tonight's QR ------------------------------------


def _checkin_state(supabase: Client, member: LineContext, code: str) -> LineCheckinState:
    night = line_checkin.night_for(supabase, code)
    if night is None:
        return LineCheckinState(state="expired")
    when = CheckinNight.model_validate(night)
    linked = rows(
        supabase.table("players")
        .select("*")
        .eq("line_user_id", member.line_user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not linked:
        return LineCheckinState(state="unlinked", night=when)
    player = Player.model_validate(linked[0])
    mine = rows(
        supabase.table("checkins")
        .select("*")
        .eq("session_id", str(night["id"]))
        .eq("player_id", str(player.id))
        .limit(1)
        .execute()
    )
    if mine and mine[0].get("checkout_time") is None:
        return LineCheckinState(
            state="in", night=when, player=player, checkin_time=mine[0]["checkin_time"]
        )
    return LineCheckinState(state="ready", night=when, player=player)


@router.get("/checkin", response_model=LineCheckinState)
def checkin_preview(c: str, supabase: SupabaseDep, member: LineMemberDep) -> LineCheckinState:
    """What the page shows after the scan, before they tap check in."""
    if not CODE.fullmatch(c):
        return LineCheckinState(state="expired")
    return _checkin_state(supabase, member, c)


@router.post("/checkin", response_model=LineCheckinState)
def checkin(
    payload: LineCheckinIn, supabase: SupabaseDep, member: LineMemberDep
) -> LineCheckinState:
    """Check themselves in to the night this QR is for. Only ever them:
    who they are comes from their LINE token, never from the request."""
    now = _checkin_state(supabase, member, payload.code)
    if now.state != "ready" or now.night is None or now.player is None:
        return now
    done = checkin_service.check_in(supabase, now.night.id, now.player.id, "line")
    return LineCheckinState(
        state="in", night=now.night, player=now.player, checkin_time=done["checkin_time"]
    )


# --- checking in by where the phone is -----------------------------------------


@router.post("/checkin/nearby", response_model=LineGpsCheckin)
def checkin_nearby(fix: GeoFix, supabase: SupabaseDep, member: LineMemberDep) -> LineGpsCheckin:
    """Check themselves in to tonight if their phone is inside the circle
    an admin pinned at the court. Who is checked in comes from their LINE
    token; only where they are comes from the request."""
    linked = rows(
        supabase.table("players")
        .select("*")
        .eq("line_user_id", member.line_user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not linked:
        return LineGpsCheckin(state="unlinked")
    player = Player.model_validate(linked[0])
    found = line_gps.nearest_night(supabase, fix.lat, fix.lng)
    if found is None:
        return LineGpsCheckin(state="none", player=player)
    night, distance = found
    when = CheckinNight.model_validate(night)
    radius = int(night["checkin_radius_m"])
    mine = rows(
        supabase.table("checkins")
        .select("*")
        .eq("session_id", str(night["id"]))
        .eq("player_id", str(player.id))
        .limit(1)
        .execute()
    )
    if mine and mine[0].get("checkout_time") is None:
        return LineGpsCheckin(
            state="in", night=when, player=player, checkin_time=mine[0]["checkin_time"]
        )
    if fix.accuracy > line_gps.MAX_ACCURACY_M:
        return LineGpsCheckin(state="weak", night=when, player=player, radius_m=radius)
    if not line_gps.inside(distance, radius, fix.accuracy):
        return LineGpsCheckin(
            state="far", night=when, player=player, distance_m=round(distance), radius_m=radius
        )
    done = checkin_service.check_in(supabase, when.id, player.id, "gps")
    return LineGpsCheckin(state="in", night=when, player=player, checkin_time=done["checkin_time"])


# --- checking out, paying, and the member's own bills ------------------------

MAX_SLIP_BYTES = 5 * 1024 * 1024
SLIP_MAX_PX = 1600  # read back for its small print; keep it legible


def _member(supabase: Client, member: LineContext) -> Player:
    linked = rows(
        supabase.table("players")
        .select("*")
        .eq("line_user_id", member.line_user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="LINE นี้ยังไม่ได้ผูกกับสมาชิกในก๊วน"
        )
    return Player.model_validate(linked[0])


def _bill(row: dict[str, Any], session: dict[str, Any]) -> LineBill:
    return LineBill(
        id=row["id"],
        night=CheckinNight.model_validate(session),
        game_count=row["game_count"],
        amount=billing_service.effective_amount(row["amount_calc"], row.get("amount_adjusted")),
        paid_status=row["paid_status"],
        slip_url=row.get("slip_url"),
        slip_sent_at=row.get("slip_sent_at"),
        slip_rejected_at=row.get("slip_rejected_at"),
        credit_used=bill_credit.used(row),
        left=0 if row["paid_status"] == "paid" else bill_credit.left_to_pay(row),
    )


@router.get("/tonight", response_model=LineTonight)
def tonight(supabase: SupabaseDep, member: LineMemberDep) -> LineTonight:
    """Their night so far: the open night (tonight, or last night for one
    that ran past midnight) they checked in to."""
    player = _member(supabase, member)
    # From the open nights (a handful at most), not from every check-in
    # they ever made: a member of some years has hundreds, and a query
    # naming them all would outgrow the request.
    open_nights = rows(supabase.table("sessions").select("*").eq("status", "open").execute())
    current = sorted(
        (n for n in open_nights if line_checkin.is_current(n)),
        key=lambda n: str(n["date"]),
        reverse=True,
    )
    session: dict[str, Any] | None = None
    checkin: dict[str, Any] | None = None
    for candidate in current:
        found = rows(
            supabase.table("checkins")
            .select("*")
            .eq("session_id", str(candidate["id"]))
            .eq("player_id", str(player.id))
            .limit(1)
            .execute()
        )
        if found:
            session, checkin = candidate, found[0]
            break
    if session is None or checkin is None:
        return LineTonight(state="none", player=player)
    when = CheckinNight.model_validate(session)
    if checkin.get("checkout_time") is None:
        games, amount = night_bill.so_far(supabase, session, player.id)
        return LineTonight(
            state="in",
            night=when,
            player=player,
            games=games,
            court_fee=session["court_fee_per_person"],
            shuttle_price=session["shuttlecock_price_per_game"],
            amount=amount,
            busy=night_bill.is_busy(supabase, UUID(str(session["id"])), player.id),
        )
    billed = rows(
        supabase.table("billings")
        .select("*")
        .eq("session_id", str(session["id"]))
        .eq("player_id", str(player.id))
        .limit(1)
        .execute()
    )
    return LineTonight(
        state="out",
        night=when,
        player=player,
        bill=_bill(billed[0], session) if billed else None,
    )


@router.post("/checkout", response_model=LineTonight)
def checkout(payload: LineCheckoutIn, supabase: SupabaseDep, member: LineMemberDep) -> LineTonight:
    """Check themselves out, and be billed for the night there and then.
    Only their own check-in, in an open current night."""
    player = _member(supabase, member)
    session = night_bill.night(supabase, payload.session_id)
    if not line_checkin.is_current(session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='คืนนี้ปิดไปแล้ว — บิลอยู่ที่ "บิลของฉัน"'
        )
    active = rows(
        supabase.table("checkins")
        .select("id")
        .eq("session_id", str(payload.session_id))
        .eq("player_id", str(player.id))
        .is_("checkout_time", "null")
        .limit(1)
        .execute()
    )
    if not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="คุณยังไม่ได้เช็คอินคืนนี้")
    if night_bill.is_busy(supabase, payload.session_id, player.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ยังมีแมตช์ของคุณที่ยังไม่จบ — จบแมตช์แล้วค่อยเช็คเอาท์นะ",
        )
    bill_credit.fit(supabase, night_bill.bill_one(supabase, payload.session_id, player.id))
    return tonight(supabase, member)


@router.get("/bills", response_model=LineBills)
def my_bills(supabase: SupabaseDep, member: LineMemberDep) -> LineBills:
    """Their own bills, newest night first — including nights they forgot
    to check out of, billed when the admin closed the night."""
    player = _member(supabase, member)
    # The latest bills only: years of nights would outgrow the request that
    # fetches their dates. One still owed stays near the top — a bill is
    # touched again whenever it is billed, adjusted or paid.
    billed = rows(
        supabase.table("billings")
        .select("*")
        .eq("player_id", str(player.id))
        .order("updated_at", desc=True)
        .limit(60)
        .execute()
    )
    ids = list({str(b["session_id"]) for b in billed})
    nights = (
        {
            str(n["id"]): n
            for n in rows(supabase.table("sessions").select("*").in_("id", ids).execute())
        }
        if ids
        else {}
    )
    bills = sorted(
        (_bill(b, nights[str(b["session_id"])]) for b in billed if str(b["session_id"]) in nights),
        key=lambda b: b.night.date,
        reverse=True,
    )[:40]
    due = sum(b.left for b in bills if b.paid_status == "unpaid" and not b.slip_url)
    return LineBills(player=player, due=round(due, 2), bills=bills)


def _own_bill(supabase: Client, member: LineContext, bill_id: UUID) -> dict[str, Any]:
    player = _member(supabase, member)
    found = rows(supabase.table("billings").select("*").eq("id", str(bill_id)).limit(1).execute())
    # Someone else's bill reads as not found, not as forbidden.
    if not found or str(found[0]["player_id"]) != str(player.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบิลนี้")
    return found[0]


def _payable(row: dict[str, Any]) -> float:
    """What is left to transfer: the bill less any credit already on it."""
    amount = billing_service.effective_amount(row["amount_calc"], row.get("amount_adjusted"))
    if row["paid_status"] == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้จ่ายแล้ว")
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้ไม่คิดเงิน")
    left = bill_credit.left_to_pay(row)
    if left <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บิลนี้จ่ายด้วยเครดิตครบแล้ว")
    return left


@router.post("/bills/{bill_id}/credit", response_model=LineBillCredit)
def pay_with_credit(bill_id: UUID, supabase: SupabaseDep, member: LineMemberDep) -> LineBillCredit:
    """Pay the bill with their club credit: all of it if the balance
    covers it, otherwise all the balance, with the rest left to transfer."""
    row = _own_bill(supabase, member, bill_id)
    session = night_bill.night(supabase, UUID(str(row["session_id"])))
    night_date = date.fromisoformat(str(session["date"]))
    note = f"คืน {night_date.day}/{night_date.month} · {row['game_count']} เกม"
    paid = bill_credit.pay(supabase, row, note)
    return LineBillCredit(bill=_bill(paid, session), balance=credit_service.balance(supabase, str(row["player_id"])))


@router.get("/bills/{bill_id}/pay", response_model=PaymentInfoResponse)
def pay_info(bill_id: UUID, supabase: SupabaseDep, member: LineMemberDep) -> PaymentInfoResponse:
    """How to pay it: the club's PromptPay QR with the amount in it, or the
    bank account — whichever the admin set in Settings."""
    row = _own_bill(supabase, member, bill_id)
    return payment_info_service.payment_info(supabase, _payable(row))


@router.post("/bills/{bill_id}/slip", response_model=LineBill)
async def send_slip(
    bill_id: UUID, file: UploadFile, supabase: SupabaseDep, member: LineMemberDep
) -> LineBill:
    """The slip of their transfer, for an admin to check and mark paid.
    Sending again replaces the slip they sent before."""
    row = _own_bill(supabase, member, bill_id)
    _payable(row)
    contents = await file.read(MAX_SLIP_BYTES + 1)  # never more than one byte past the limit
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="รูปใหญ่เกินไป (ไม่เกิน 5MB)"
        )
    try:
        slip = resize_jpeg(contents, SLIP_MAX_PX)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์นี้ไม่ใช่รูปภาพ"
        ) from None
    path = f"bill-slip-{uuid4().hex}.jpg"
    bucket = supabase.storage.from_(night_bill.SLIP_BUCKET)
    bucket.upload(path, slip, {"content-type": "image/jpeg", "upsert": "false"})
    url = str(bucket.get_public_url(path))
    updated = rows(
        supabase.table("billings")
        .update(
            {
                "slip_url": url,
                "slip_sent_at": datetime.now(UTC).isoformat(),
                "slip_rejected_at": None,
            }
        )
        .eq("id", str(bill_id))
        .execute()
    )
    night_bill.forget_slip(supabase, row.get("slip_url"))
    session = night_bill.night(supabase, UUID(str(row["session_id"])))
    return _bill(updated[0], session)
