"""The /line page: a member opens it inside LINE (LIFF) and links their LINE
account to their name in the club.

POST /session trades LINE's ID token for one of ours, after LINE itself
has vouched for it (services/line_auth.py). Everything else here takes that
token. A link is only ever requested here; an admin approves it
(routers/admin/line_admin.py), since otherwise anyone could claim anyone.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from supabase import Client

from app.config import get_settings
from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import LineConfig, LineSessionIn, LineStatus, LinkOption, LinkPick, LinkRequest
from app.models.player import Player
from app.security import create_line_token
from app.services import line_auth

router = APIRouter(prefix="/api/line", tags=["line"])

TABLE = "line_link_requests"


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
    return LineStatus(
        line_name=line_name,
        line_picture=picture or (pending or {}).get("line_picture"),
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
