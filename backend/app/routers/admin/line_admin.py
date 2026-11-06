"""The admin's side of LINE links: approve or refuse what members picked on
the /line page, and undo a link made by mistake."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.line import (
    CheckinNight,
    CheckinQr,
    CheckinSpot,
    CheckinSpotIn,
    JoinApprove,
    JoinRequestAdmin,
    LineInvite,
    LineLink,
    LinkRequestAdmin,
)
from app.models.player import Player
from app.routers.admin.players_admin import check_nickname
from app.services import line_auth, line_checkin, line_gps, line_join, promptpay_service
from app.services.elo_service import SCORE_FLOOR, STARTING_SCORE, get_tier
from app.services.promptpay_service import generate_qr_data_uri
from app.services.session_state import ensure_session_open

router = APIRouter(prefix="/api/admin/line", tags=["admin-line"])

TABLE = "line_link_requests"
JOINS = "line_join_requests"


def _now() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/requests", response_model=list[LinkRequestAdmin])
def pending_requests(supabase: SupabaseDep, admin: AdminDep) -> list[LinkRequestAdmin]:
    pending = rows(
        supabase.table(TABLE).select("*").eq("status", "pending").order("created_at").execute()
    )
    ids = list({str(r["player_id"]) for r in pending})
    players = (
        {
            str(p["id"]): p
            for p in rows(supabase.table("players").select("*").in_("id", ids).execute())
        }
        if ids
        else {}
    )
    return [
        LinkRequestAdmin(
            id=r["id"],
            line_name=r["line_name"],
            line_picture=r.get("line_picture"),
            player=Player.model_validate(players[str(r["player_id"])]),
            created_at=r["created_at"],
        )
        for r in pending
        if r.get("status") == "pending" and str(r["player_id"]) in players
    ]


def _request(supabase: SupabaseDep, request_id: UUID) -> dict[str, Any]:
    found = rows(supabase.table(TABLE).select("*").eq("id", str(request_id)).limit(1).execute())
    if not found or found[0].get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="คำขอนี้ถูกจัดการไปแล้ว — รีเฟรชหน้า"
        )
    return found[0]


@router.post("/requests/{request_id}/approve", response_model=Player)
def approve(request_id: UUID, http: Request, supabase: SupabaseDep, admin: AdminDep) -> Player:
    req = _request(supabase, request_id)
    line_user_id, player_id = str(req["line_user_id"]), str(req["player_id"])
    player = rows(supabase.table("players").select("*").eq("id", player_id).limit(1).execute())
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบสมาชิกคนนี้แล้ว")
    if player[0].get("line_user_id") and player[0]["line_user_id"] != line_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{player[0]['nickname']} ผูกกับ LINE อื่นอยู่แล้ว — ยกเลิกอันเดิมก่อน",
        )
    other = rows(
        supabase.table("players")
        .select("id, nickname")
        .eq("line_user_id", line_user_id)
        .limit(1)
        .execute()
    )
    if other and str(other[0]["id"]) != player_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"LINE นี้ผูกกับ {other[0]['nickname']} อยู่แล้ว",
        )
    linked = rows(
        supabase.table("players")
        .update({"line_user_id": line_user_id, "line_name": req["line_name"]})
        .eq("id", player_id)
        .execute()
    )
    decided = {"decided_at": _now(), "decided_by": str(admin.admin_id)}
    supabase.table(TABLE).update({"status": "approved", **decided}).eq(
        "id", str(request_id)
    ).execute()
    # Anyone else who claimed the same name was wrong.
    supabase.table(TABLE).update({"status": "rejected", **decided}).eq("player_id", player_id).eq(
        "status", "pending"
    ).execute()
    http.state.activity_detail = {"player": player[0]["nickname"], "line": req["line_name"]}
    return Player.model_validate(linked[0])


@router.post("/requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject(request_id: UUID, http: Request, supabase: SupabaseDep, admin: AdminDep) -> None:
    req = _request(supabase, request_id)
    supabase.table(TABLE).update(
        {"status": "rejected", "decided_at": _now(), "decided_by": str(admin.admin_id)}
    ).eq("id", str(request_id)).execute()
    http.state.activity_detail = {"line": req["line_name"]}


@router.get("/links", response_model=list[LineLink])
def links(supabase: SupabaseDep, admin: AdminDep) -> list[LineLink]:
    linked = rows(supabase.table("players").select("id, line_user_id, line_name").execute())
    return [
        LineLink(player_id=p["id"], line_name=p.get("line_name"))
        for p in linked
        if p.get("line_user_id")
    ]


@router.get("/invite", response_model=LineInvite)
def invite(admin: AdminDep) -> LineInvite:
    """The QR that sends a member to link their LINE."""
    if not line_auth.configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ยังไม่ได้ตั้งค่า LINE"
        )
    url = line_checkin.invite_url()
    return LineInvite(url=url, qr_modules=promptpay_service.qr_modules(url))


@router.post("/players/{player_id}/unlink", response_model=Player)
def unlink(player_id: UUID, http: Request, supabase: SupabaseDep, admin: AdminDep) -> Player:
    found = rows(
        supabase.table("players")
        .update({"line_user_id": None, "line_name": None})
        .eq("id", str(player_id))
        .execute()
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    http.state.activity_detail = {"player": found[0]["nickname"]}
    return Player.model_validate(found[0])


# --- sign-ups from people not in the club yet --------------------------------


@router.get("/joins", response_model=list[JoinRequestAdmin])
def pending_joins(supabase: SupabaseDep, admin: AdminDep) -> list[JoinRequestAdmin]:
    pending = rows(
        supabase.table(JOINS).select("*").eq("status", "pending").order("created_at").execute()
    )
    return [JoinRequestAdmin.model_validate(r) for r in pending if r.get("status") == "pending"]


def _join(supabase: SupabaseDep, join_id: UUID) -> dict[str, Any]:
    found = rows(supabase.table(JOINS).select("*").eq("id", str(join_id)).limit(1).execute())
    if not found or found[0].get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ใบสมัครนี้ถูกจัดการไปแล้ว — รีเฟรชหน้า"
        )
    return found[0]


@router.post("/joins/{join_id}/approve", response_model=Player)
def approve_join(
    join_id: UUID, payload: JoinApprove, http: Request, supabase: SupabaseDep, admin: AdminDep
) -> Player:
    """Take them into the club: the player is created here, already linked
    to the LINE account that applied."""
    req = _join(supabase, join_id)
    line_user_id = str(req["line_user_id"])
    linked = rows(
        supabase.table("players").select("nickname").eq("line_user_id", line_user_id).execute()
    )
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"LINE นี้เป็นสมาชิก {linked[0]['nickname']} อยู่แล้ว — ปฏิเสธใบสมัครนี้ได้เลย",
        )
    # Checked again: someone may have taken the name since they applied.
    nickname = check_nickname(supabase, str(req["nickname"]))
    elo_score = (
        max(SCORE_FLOOR, payload.elo_score) if payload.elo_score is not None else STARTING_SCORE
    )
    created = rows(
        supabase.table("players")
        .insert(
            {
                "nickname": nickname,
                "dominant_hand": req.get("dominant_hand"),
                "instagram": req.get("instagram"),
                "tiktok": req.get("tiktok"),
                "quote": req.get("quote"),
                "avatar_url": req.get("photo_url"),
                "elo_score": elo_score,
                "elo_level": get_tier(elo_score),
                "is_active": True,
                "line_user_id": line_user_id,
                "line_name": req["line_name"],
            }
        )
        .execute()
    )
    player = created[0]
    supabase.table(JOINS).update(
        {
            "status": "approved",
            "player_id": str(player["id"]),
            "decided_at": _now(),
            "decided_by": str(admin.admin_id),
        }
    ).eq("id", str(join_id)).execute()
    http.state.activity_detail = {"player": nickname, "line": req["line_name"]}
    return Player.model_validate(player)


@router.post("/joins/{join_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_join(join_id: UUID, http: Request, supabase: SupabaseDep, admin: AdminDep) -> None:
    req = _join(supabase, join_id)
    supabase.table(JOINS).update(
        {"status": "rejected", "decided_at": _now(), "decided_by": str(admin.admin_id)}
    ).eq("id", str(join_id)).execute()
    line_join.remove_photo(supabase, req.get("photo_url"))
    http.state.activity_detail = {"nickname": req["nickname"], "line": req["line_name"]}


# --- tonight's check-in QR ---------------------------------------------------


def _qr(supabase: SupabaseDep, session_id: UUID, *, fresh: bool) -> CheckinQr:
    if not line_auth.configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ยังไม่ได้ตั้งค่า LINE"
        )
    # A closed night is billed: a QR for it would check people in to nothing.
    ensure_session_open(supabase, session_id)
    night = rows(
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )[0]
    code = night.get("line_checkin_code")
    if fresh or not code:
        code = line_checkin.new_code()
        supabase.table("sessions").update({"line_checkin_code": code}).eq(
            "id", str(session_id)
        ).execute()
    url = line_checkin.checkin_url(code)
    return CheckinQr(
        night=CheckinNight.model_validate(night),
        code=code,
        url=url,
        qr=generate_qr_data_uri(url),
        qr_modules=promptpay_service.qr_modules(url),
    )


@router.get("/checkin-qr", response_model=CheckinQr)
def checkin_qr(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> CheckinQr:
    """Tonight's QR, made the first time it is asked for."""
    return _qr(supabase, session_id, fresh=False)


@router.post("/checkin-qr/rotate", response_model=CheckinQr)
def rotate_checkin_qr(
    session_id: UUID, http: Request, supabase: SupabaseDep, admin: AdminDep
) -> CheckinQr:
    """A new QR for tonight; the old one stops working (it was shared)."""
    made = _qr(supabase, session_id, fresh=True)
    http.state.activity_detail = {"session": str(made.night.date)}
    return made


# --- tonight's pin, for checking in by location -------------------------------


def _spot(night: dict[str, Any]) -> CheckinSpot | None:
    if night.get("checkin_lat") is None:
        return None
    return CheckinSpot(
        lat=night["checkin_lat"],
        lng=night["checkin_lng"],
        radius_m=night["checkin_radius_m"],
        accuracy_m=night.get("checkin_accuracy_m"),
        pinned_at=night.get("checkin_pinned_at"),
    )


def _night(supabase: SupabaseDep, session_id: UUID) -> dict[str, Any]:
    found = rows(
        supabase.table("sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return found[0]


@router.get("/checkin-spot", response_model=CheckinSpot | None)
def checkin_spot(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> CheckinSpot | None:
    return _spot(_night(supabase, session_id))


@router.put("/checkin-spot", response_model=CheckinSpot)
def pin_checkin_spot(
    session_id: UUID, payload: CheckinSpotIn, http: Request, supabase: SupabaseDep, admin: AdminDep
) -> CheckinSpot:
    """Pin tonight's court where the admin's phone is now."""
    _night(supabase, session_id)
    # A closed night is billed: a pin for it would check people in to nothing.
    ensure_session_open(supabase, session_id)
    if payload.accuracy > line_gps.MAX_ACCURACY_M:
        raise HTTPException(
            status_code=422,
            detail="GPS ยังไม่แม่น — ลองออกไปที่โล่งหรือรอสักครู่แล้วปักใหม่",
        )
    updated = (
        supabase.table("sessions")
        .update(
            {
                "checkin_lat": payload.lat,
                "checkin_lng": payload.lng,
                "checkin_radius_m": payload.radius_m,
                "checkin_accuracy_m": round(payload.accuracy),
                "checkin_pinned_at": _now(),
            }
        )
        .eq("id", str(session_id))
        .execute()
    )
    spot = _spot(rows(updated)[0])
    assert spot is not None
    http.state.activity_detail = {"radius_m": payload.radius_m}
    return spot


@router.delete("/checkin-spot", status_code=status.HTTP_204_NO_CONTENT)
def unpin_checkin_spot(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Stop checking in by location tonight."""
    _night(supabase, session_id)
    supabase.table("sessions").update(
        {
            "checkin_lat": None,
            "checkin_lng": None,
            "checkin_radius_m": None,
            "checkin_accuracy_m": None,
            "checkin_pinned_at": None,
        }
    ).eq("id", str(session_id)).execute()
