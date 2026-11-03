"""The /line page: a member opens it inside LINE (LIFF) and links their LINE
account to their name in the club.

POST /session trades LINE's ID token for one of ours, after LINE itself
has vouched for it (services/line_auth.py). Everything else here takes that
token. A link is only ever requested here; an admin approves it
(routers/admin/line_admin.py), since otherwise anyone could claim anyone.
"""

import re
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status
from supabase import Client

from app.config import get_settings
from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import (
    CheckinNight,
    JoinApplication,
    JoinIn,
    LineCheckinIn,
    LineCheckinState,
    LineConfig,
    LineContext,
    LineSessionIn,
    LineStatus,
    LinkOption,
    LinkPick,
    LinkRequest,
)
from app.models.player import Player
from app.routers.admin.players_admin import check_nickname
from app.security import create_line_token
from app.services import checkin_service, line_auth, line_checkin, line_join

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


@router.post("/session", response_model=LineStatus)
def start_session(payload: LineSessionIn, supabase: SupabaseDep) -> LineStatus:
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
    nickname = check_nickname(supabase, payload.nickname)
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
    contents = await file.read()
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
