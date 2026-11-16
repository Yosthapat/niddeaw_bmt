"""The tournament's own admin screens (/admin/tournament). Every route here
takes TournamentAdminDep: a club admin without the tournament right is
refused, and nothing here reads the club's money, bills or credit.

Writes under /api/admin/tournament are logged with area = 'tournament'
(middleware/activity_log.py), so they show on this side's log only.
"""

import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from supabase import Client

from app.db_utils import rows
from app.deps import SupabaseDep, TournamentAdminDep
from app.models.tournament import (
    AdminActivity,
    CallIn,
    CheckInIn,
    CouponSaleIn,
    GameDay,
    ResultIn,
    DrawState,
    PlaceIn,
    PublishIn,
    AdminSignUpIn,
    AdminTeam,
    EntrantUpdate,
    LevelIn,
    LevelUpdate,
    Money,
    MoneyIn,
    MoneySummary,
    PlayerHit,
    TeamUpdate,
    Tournament,
    TournamentCreate,
    TournamentUpdate,
    WithdrawIn,
)
from app.services import promptpay_service
from app.services import tournament_draw as td
from app.services import tournament_play as tp
from app.services import tournament_service as ts
from app.services import tournament_views as views
from app.services.image_service import resize_jpeg

router = APIRouter(prefix="/api/admin/tournament", tags=["admin-tournament"])

RECEIPT_BUCKET = "receipts"
MAX_FILE_BYTES = 5 * 1024 * 1024
FEE_FIELDS = {"entry_fee", "shuttle_fee"}
STATUS_LABEL = {
    "invited": "รอคู่ตอบ",
    "awaiting_payment": "รอโอน",
    "slip_review": "รอตรวจสลิป",
    "confirmed": "ยืนยันแล้ว",
    "waitlist": "ตัวสำรอง",
    "cancelled": "ยกเลิก",
    "withdrawn": "ถอนตัว",
}
PAY_LABEL = {
    "unpaid": "ยังไม่จ่าย",
    "slip_sent": "ส่งสลิปแล้ว",
    "paid": "จ่ายแล้ว",
    "rejected": "สลิปไม่ผ่าน",
    "refunded": "คืนเงินแล้ว",
}


# --- the event ---------------------------------------------------------------


@router.get("/tournaments", response_model=list[Tournament])
def list_tournaments(supabase: SupabaseDep, admin: TournamentAdminDep) -> list[Tournament]:
    found = rows(supabase.table(ts.TOURNAMENTS).select("*").order("starts_on", desc=True).execute())
    return [views.tournament_model(supabase, r) for r in found]


@router.post("/tournaments", response_model=Tournament, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreate, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Tournament:
    if payload.opens_at and payload.opens_at >= payload.closes_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="วันเปิดรับต้องก่อนวันปิดรับ")
    row = ts.create_tournament(supabase, payload.model_dump(mode="json"), str(admin.admin_id))
    return views.tournament_model(supabase, row)


@router.get("/tournaments/{tournament_id}", response_model=Tournament)
def get_tournament(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Tournament:
    ts.sweep(supabase, str(tournament_id))
    return views.tournament_model(supabase, ts.tournament(supabase, str(tournament_id)))


@router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tournament(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> None:
    """A tournament set up to try things out goes, with everything in it —
    levels, teams, entries, money, matches. Not once it is being played or
    is over: that is the record of a real day."""
    tid = str(tournament_id)
    row = ts.tournament(supabase, tid)
    if row["status"] in ("running", "done"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="งานที่กำลังแข่งหรือจบแล้วลบไม่ได้",
        )
    # The slips' QR codes go too, or a slip from the trial would read as a
    # duplicate when the same person pays for the real one.
    entrant_ids = [str(e["id"]) for e in ts.entrants(supabase, tid)]
    if entrant_ids:
        supabase.table("slip_checks").delete().eq("kind", "tournament").in_(
            "target_id", entrant_ids
        ).execute()
    supabase.table(ts.TOURNAMENTS).delete().eq("id", tid).execute()


@router.patch("/tournaments/{tournament_id}", response_model=Tournament)
def update_tournament(
    tournament_id: UUID, payload: TournamentUpdate, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Tournament:
    tid = str(tournament_id)
    current = ts.tournament(supabase, tid)
    changes = payload.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีอะไรให้แก้")
    for key in FEE_FIELDS & set(changes):
        if int(changes[key]) != int(current[key]) and ts.fees_locked(supabase, tid):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="มีคนจ่ายค่าสมัครแล้ว ราคาค่าสมัครและค่าลูกแก้ไม่ได้ (กันคนจ่ายไม่เท่ากัน)",
            )
    if "promptpay_id" in changes and changes["promptpay_id"] is not None:
        changes["promptpay_id"] = (
            "".join(ch for ch in changes["promptpay_id"] if ch.isdigit()) or None
        )
    after = {**current, **changes}
    opens, closes = ts.when(after.get("opens_at")), ts.when(after["closes_at"])
    if opens and closes and opens >= closes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="วันเปิดรับต้องก่อนวันปิดรับ")
    if after.get("promptpay_id") or after.get("promptpay_type"):
        problem = promptpay_service.id_problem(
            after.get("promptpay_id"), after.get("promptpay_type"), "promptpay"
        )
        if problem:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)
    if changes.get("status") == "open" and not (
        after.get("promptpay_id") and after.get("promptpay_type")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ตั้งบัญชี PromptPay ของงานก่อน ถึงจะเปิดรับสมัครได้",
        )
    supabase.table(ts.TOURNAMENTS).update(changes).eq("id", tid).execute()
    return views.tournament_model(supabase, ts.tournament(supabase, tid))


@router.post("/tournaments/{tournament_id}/levels", response_model=Tournament)
def add_level(
    tournament_id: UUID, payload: LevelIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Tournament:
    tid = str(tournament_id)
    existing = ts.levels(supabase, tid)
    supabase.table(ts.LEVELS).insert(
        {
            "id": str(uuid4()),
            "tournament_id": tid,
            "sort": 1 + max((int(lv.get("sort") or 0) for lv in existing), default=-1),
            **payload.model_dump(),
        }
    ).execute()
    return views.tournament_model(supabase, ts.tournament(supabase, tid))


@router.patch("/tournaments/{tournament_id}/levels/{level_id}", response_model=Tournament)
def update_level(
    tournament_id: UUID,
    level_id: UUID,
    payload: LevelUpdate,
    supabase: SupabaseDep,
    admin: TournamentAdminDep,
) -> Tournament:
    tid, lid = str(tournament_id), str(level_id)
    current = ts.level(supabase, tid, lid)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีอะไรให้แก้")
    after = {**current, **changes}
    if (
        after.get("min_elo") is not None
        and after.get("max_elo") is not None
        and after["min_elo"] >= after["max_elo"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ช่วง ELO ต้องเริ่มต่ำกว่าที่จบ"
        )
    supabase.table(ts.LEVELS).update(changes).eq("id", lid).execute()
    if "max_teams" in changes and int(changes["max_teams"]) != int(current["max_teams"]):
        ts.resize_level(supabase, tid, ts.level(supabase, tid, lid))
    return views.tournament_model(supabase, ts.tournament(supabase, tid))


@router.delete("/tournaments/{tournament_id}/levels/{level_id}", response_model=Tournament)
def delete_level(
    tournament_id: UUID, level_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Tournament:
    tid, lid = str(tournament_id), str(level_id)
    ts.level(supabase, tid, lid)
    if any(str(t["level_id"]) == lid for t in ts.teams(supabase, tid)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="มือนี้มีทีมสมัครแล้ว ลบไม่ได้")
    supabase.table(ts.LEVELS).delete().eq("id", lid).execute()
    return views.tournament_model(supabase, ts.tournament(supabase, tid))


# --- teams -------------------------------------------------------------------


@router.get("/tournaments/{tournament_id}/teams", response_model=list[AdminTeam])
def list_teams(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    tid = str(tournament_id)
    ts.tournament(supabase, tid)
    ts.sweep(supabase, tid)
    return views.admin_teams(supabase, tid)


@router.get("/tournaments/{tournament_id}/teams.csv")
def export_teams(tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> Response:
    """Every player of every live team, for score sheets or the insurer.
    The UTF-8 BOM makes Excel read the Thai correctly."""
    tid = str(tournament_id)
    row = ts.tournament(supabase, tid)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "มือ",
            "ทีม",
            "สถานะทีม",
            "บทบาท",
            "ชื่อเล่น",
            "ชื่อจริง",
            "นามสกุล",
            "เบอร์โทร",
            "ELO",
            "ยอด",
            "สถานะจ่าย",
        ]
    )
    for t in views.admin_teams(supabase, tid):
        if t.status not in ts.LIVE:
            continue
        for e in t.entrants:
            writer.writerow(
                [
                    t.level_name, t.name, STATUS_LABEL[t.status], "หัวหน้าทีม" if e.role == "captain" else "คู่",
                    e.nickname, e.first_name or "", e.last_name or "", e.phone or "", e.elo or "", e.share,
                    PAY_LABEL[e.pay_status],
                ]
            )  # fmt: skip
    filename = f"tournament-{row['starts_on']}.csv"
    return Response(
        content="﻿" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tournaments/{tournament_id}/players", response_model=list[PlayerHit])
def search_players(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[PlayerHit]:
    """Everyone in the club's list, for signing a pair up: their nickname,
    rating and games, and nothing of the club's money."""
    tid = str(tournament_id)
    ts.tournament(supabase, tid)
    taken = {str(e["player_id"]) for e in ts.entrants(supabase, tid) if e.get("active")}
    found = rows(supabase.table("players").select("*").eq("is_active", True).execute())
    return sorted(
        (
            PlayerHit(
                player_id=p["id"],
                nickname=p["nickname"],
                avatar_url=p.get("avatar_url"),
                elo=int(p.get("elo_score") or 0),
                elo_level=str(p.get("elo_level") or ""),
                games=int(p.get("games") or 0),
                line_linked=bool(p.get("line_user_id")),
                taken=str(p["id"]) in taken,
            )
            for p in found
            if p.get("is_active", True)
        ),
        key=lambda h: h.nickname.lower(),
    )


def _player(supabase: Client, player_id: UUID) -> dict[str, Any]:
    found = rows(supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้เล่นนี้")
    return found[0]


@router.post(
    "/tournaments/{tournament_id}/teams",
    response_model=list[AdminTeam],
    status_code=status.HTTP_201_CREATED,
)
def sign_up_pair(
    tournament_id: UUID, payload: AdminSignUpIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    """A pair signed up at the desk, for players without LINE: the same rules
    as from LINE (games played, level), both players' details given here."""
    tid = str(tournament_id)
    row = ts.tournament(supabase, tid)
    if row["status"] == "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="งานนี้จบไปแล้ว")
    ts.sweep(supabase, tid)
    captain, partner = (
        _player(supabase, payload.captain.player_id),
        _player(supabase, payload.partner.player_id),
    )
    lv = ts.check_pair(
        supabase, row, ts.Pair(captain, partner), str(payload.level_id), line_needed=False
    )
    team_id = ts.create_team(
        supabase,
        row,
        str(lv["id"]),
        payload.team_name,
        (captain, payload.captain.model_dump(exclude={"player_id"})),
        (partner, payload.partner.model_dump(exclude={"player_id"})),
        admin_id=str(admin.admin_id),
    )
    if payload.paid_via != "unpaid":
        for e in ts.team_entrants(supabase, team_id):
            ts.mark_paid(supabase, e, str(admin.admin_id), payload.paid_via)
    return views.admin_teams(supabase, tid)


@router.patch("/teams/{team_id}", response_model=list[AdminTeam])
def update_team(
    team_id: UUID, payload: TeamUpdate, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    t = ts.team(supabase, str(team_id))
    tid = str(t["tournament_id"])
    changes = payload.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีอะไรให้แก้")
    target = str(changes.get("level_id") or t["level_id"])
    new_level = ts.level(supabase, tid, target)
    moving = target != str(t["level_id"])
    if moving and t["status"] in ts.SEATED:
        if ts.seats_taken(ts.teams(supabase, tid), target) >= int(new_level["max_teams"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"มือ {new_level['name']} เต็มแล้ว"
            )
    supabase.table(ts.TEAMS).update(changes).eq("id", str(t["id"])).execute()
    if moving:
        ts.promote(supabase, tid, ts.level(supabase, tid, str(t["level_id"])))
    return views.admin_teams(supabase, tid)


@router.post("/teams/{team_id}/withdraw", response_model=list[AdminTeam])
def withdraw_team(
    team_id: UUID, payload: WithdrawIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    """Any time, unlike from LINE. `no_refund` keeps what they paid."""
    t = ts.team(supabase, str(team_id))
    if t["status"] not in ts.LIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ทีมนี้จบไปแล้ว")
    ts.end_team(supabase, t, "withdrawn", no_refund=payload.no_refund)
    return views.admin_teams(supabase, str(t["tournament_id"]))


@router.patch("/entrants/{entrant_id}", response_model=list[AdminTeam])
def update_entrant(
    entrant_id: UUID, payload: EntrantUpdate, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    e = ts.entrant(supabase, str(entrant_id))
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีอะไรให้แก้")
    supabase.table(ts.ENTRANTS).update(changes).eq("id", str(e["id"])).execute()
    return views.admin_teams(supabase, str(e["tournament_id"]))


@router.post("/entrants/{entrant_id}/approve", response_model=list[AdminTeam])
def approve_slip(
    entrant_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    e = ts.entrant(supabase, str(entrant_id))
    ts.mark_paid(supabase, e, str(admin.admin_id), "transfer")
    return views.admin_teams(supabase, str(e["tournament_id"]))


@router.post("/entrants/{entrant_id}/reject", response_model=list[AdminTeam])
def reject_slip(
    entrant_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    e = ts.entrant(supabase, str(entrant_id))
    ts.reject(supabase, e, str(admin.admin_id))
    return views.admin_teams(supabase, str(e["tournament_id"]))


@router.post("/entrants/{entrant_id}/cash", response_model=list[AdminTeam])
def take_cash(
    entrant_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[AdminTeam]:
    """Their half paid in cash at the desk."""
    e = ts.entrant(supabase, str(entrant_id))
    t = ts.team(supabase, str(e["team_id"]))
    if t["status"] not in ts.LIVE or t["status"] == "invited":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ทีมนี้ยังไม่ถึงขั้นจ่าย หรือจบไปแล้ว"
        )
    ts.mark_paid(supabase, e, str(admin.admin_id), "cash")
    return views.admin_teams(supabase, str(e["tournament_id"]))


async def _store(supabase: Client, file: UploadFile, prefix: str) -> str:
    contents = await file.read(MAX_FILE_BYTES + 1)
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="รูปใหญ่เกินไป (ไม่เกิน 5MB)"
        )
    try:
        image = resize_jpeg(contents, 1600)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์นี้ไม่ใช่รูปภาพ"
        ) from None
    path = f"tournament/{prefix}-{uuid4().hex}.jpg"
    bucket = supabase.storage.from_(RECEIPT_BUCKET)
    bucket.upload(path, image, {"content-type": "image/jpeg", "upsert": "false"})
    return str(bucket.get_public_url(path))


@router.post("/entrants/{entrant_id}/refund", response_model=list[AdminTeam])
async def refund_entrant(
    entrant_id: UUID,
    supabase: SupabaseDep,
    admin: TournamentAdminDep,
    file: UploadFile | None = None,
) -> list[AdminTeam]:
    """Their fee given back, by transfer or cash; the transfer's slip, if
    attached, is kept with the expense."""
    e = ts.entrant(supabase, str(entrant_id))
    url = await _store(supabase, file, "refund") if file is not None else None
    ts.refund(supabase, e, str(admin.admin_id), url)
    return views.admin_teams(supabase, str(e["tournament_id"]))


# --- phase 2: groups and the match list ----------------------------------------


@router.get("/tournaments/{tournament_id}/draw", response_model=DrawState)
def draw_state(tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> DrawState:
    return views.draw_state(supabase, str(tournament_id), sweep=True)


@router.post("/tournaments/{tournament_id}/levels/{level_id}/draw", response_model=DrawState)
def draw_level(
    tournament_id: UUID, level_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    """Draw a level's groups by lot from its confirmed teams — again, if it
    was drawn before, as long as no match list has been made."""
    td.draw_level(supabase, str(tournament_id), str(level_id))
    return views.draw_state(supabase, str(tournament_id))


@router.delete("/tournaments/{tournament_id}/levels/{level_id}/draw", response_model=DrawState)
def clear_draw(
    tournament_id: UUID, level_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    td.clear_level(supabase, str(tournament_id), str(level_id))
    return views.draw_state(supabase, str(tournament_id))


@router.put("/teams/{team_id}/group", response_model=DrawState)
def place_team(
    team_id: UUID, payload: PlaceIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    """Move a team into a group's place, swapping with whoever holds it."""
    t = ts.team(supabase, str(team_id))
    td.move(supabase, str(team_id), payload.group_label, payload.group_pos)
    return views.draw_state(supabase, str(t["tournament_id"]))


@router.post("/tournaments/{tournament_id}/schedule", response_model=DrawState)
def make_schedule(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    td.build(supabase, str(tournament_id))
    return views.draw_state(supabase, str(tournament_id))


@router.delete("/tournaments/{tournament_id}/schedule", response_model=DrawState)
def clear_schedule(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    td.clear(supabase, str(tournament_id))
    return views.draw_state(supabase, str(tournament_id))


@router.post("/tournaments/{tournament_id}/publish", response_model=DrawState)
def publish(
    tournament_id: UUID, payload: PublishIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> DrawState:
    """Show the groups and the match list on /tournament and in LINE, or hide them again."""
    td.publish(supabase, str(tournament_id), payload.on)
    return views.draw_state(supabase, str(tournament_id))


# --- phase 3: the day ----------------------------------------------------------


@router.get("/tournaments/{tournament_id}/day", response_model=GameDay)
def game_day(tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> GameDay:
    return views.game_day(supabase, str(tournament_id))


def _day_of(supabase: Client, match_id: UUID) -> GameDay:
    return views.game_day(supabase, str(tp.match(supabase, str(match_id))["tournament_id"]))


@router.post("/matches/{match_id}/call", response_model=GameDay)
def call_match(
    match_id: UUID, payload: CallIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> GameDay:
    tp.call(supabase, str(match_id), payload.court)
    return _day_of(supabase, match_id)


@router.post("/matches/{match_id}/call-again", response_model=GameDay)
def call_match_again(match_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> GameDay:
    tp.call_again(supabase, str(match_id))
    return _day_of(supabase, match_id)


@router.post("/matches/{match_id}/uncall", response_model=GameDay)
def uncall_match(match_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> GameDay:
    tp.uncall(supabase, str(match_id))
    return _day_of(supabase, match_id)


@router.post("/matches/{match_id}/result", response_model=GameDay)
def match_result(
    match_id: UUID, payload: ResultIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> GameDay:
    """From the signed score sheet — or a walkover — and again to correct it,
    until a match it decides has been called."""
    tp.record(
        supabase,
        str(match_id),
        payload.sets,
        payload.shuttles,
        str(admin.admin_id),
        payload.walkover_winner,
    )
    return _day_of(supabase, match_id)


@router.post("/teams/{team_id}/coupons/sell", response_model=GameDay)
async def sell_coupons(
    team_id: UUID,
    supabase: SupabaseDep,
    admin: TournamentAdminDep,
    quantity: int = 1,
    paid_via: str = "cash",
    file: UploadFile | None = None,
) -> GameDay:
    """Extra coupon sets at the desk, at the price set for the day; the
    transfer's slip, if there is one, is kept with the income."""
    sale = CouponSaleIn(quantity=quantity, paid_via=paid_via)  # type: ignore[arg-type]
    url = await _store(supabase, file, "coupons") if file is not None else None
    tp.sell_sets(supabase, str(team_id), sale.quantity, sale.paid_via, url, str(admin.admin_id))
    return views.game_day(supabase, str(ts.team(supabase, str(team_id))["tournament_id"]))


@router.post("/teams/{team_id}/arrived", response_model=GameDay)
def check_in_team(
    team_id: UUID, payload: CheckInIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> GameDay:
    """The desk marks a team here, or takes the mark back."""
    try:
        row = tp.check_in(supabase, str(team_id), payload.arrived)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return views.game_day(supabase, str(row["tournament_id"]))


@router.post("/teams/{team_id}/coupons/return", response_model=GameDay)
async def return_coupons(
    team_id: UUID,
    supabase: SupabaseDep,
    admin: TournamentAdminDep,
    quantity: int = 1,
    paid_via: str = "cash",
    file: UploadFile | None = None,
) -> GameDay:
    """Coupons a team didn't use, bought back at the day's price."""
    sale = CouponSaleIn(quantity=quantity, paid_via=paid_via)  # type: ignore[arg-type]
    url = await _store(supabase, file, "coupon-refund") if file is not None else None
    tp.buy_back(supabase, str(team_id), sale.quantity, sale.paid_via, url, str(admin.admin_id))
    return views.game_day(supabase, str(ts.team(supabase, str(team_id))["tournament_id"]))


# --- money -------------------------------------------------------------------


def _money(row: dict[str, Any]) -> Money:
    return Money.model_validate({**row, "automatic": row.get("entrant_id") is not None})


@router.get("/tournaments/{tournament_id}/money", response_model=list[Money])
def list_money(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> list[Money]:
    tid = str(tournament_id)
    ts.tournament(supabase, tid)
    found = rows(supabase.table(ts.MONEY).select("*").eq("tournament_id", tid).execute())
    found.sort(key=lambda r: (str(r["entry_date"]), str(r.get("created_at") or "")), reverse=True)
    return [_money(r) for r in found]


@router.post(
    "/tournaments/{tournament_id}/money", response_model=Money, status_code=status.HTTP_201_CREATED
)
def add_money(
    tournament_id: UUID, payload: MoneyIn, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Money:
    tid = str(tournament_id)
    ts.tournament(supabase, tid)
    income = {"sponsor", "other_income", "extra_shuttles"}
    if (payload.direction == "income") != (payload.category in income):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="หมวดนี้ไม่ตรงกับรายรับ/รายจ่าย"
        )
    row = {
        "id": str(uuid4()),
        "tournament_id": tid,
        **payload.model_dump(mode="json"),
        "entrant_id": None,
        "team_id": None,
        "quantity": None,
        "unit_price": None,
        "receipt_url": None,
        "created_by": str(admin.admin_id),
        "created_at": ts.iso(ts.now()),
    }
    if payload.direction == "expense" and row.get("paid_by") is None:
        row["paid_by"] = str(admin.admin_id)
    supabase.table(ts.MONEY).insert(row).execute()
    return _money(row)


def _manual(supabase: Client, money_id: UUID) -> dict[str, Any]:
    found = rows(supabase.table(ts.MONEY).select("*").eq("id", str(money_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการนี้")
    if found[0].get("entrant_id") is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="รายการนี้มาจากใบสมัคร แก้ที่ตัวใบสมัครแทน"
        )
    return found[0]


@router.delete("/money/{money_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_money(money_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep) -> None:
    _manual(supabase, money_id)
    supabase.table(ts.MONEY).delete().eq("id", str(money_id)).execute()


@router.post("/money/{money_id}/receipt", response_model=Money)
async def money_receipt(
    money_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: TournamentAdminDep
) -> Money:
    row = _manual(supabase, money_id)
    url = await _store(supabase, file, "receipt")
    supabase.table(ts.MONEY).update({"receipt_url": url}).eq("id", str(money_id)).execute()
    return _money({**row, "receipt_url": url})


@router.get("/tournaments/{tournament_id}/summary", response_model=MoneySummary)
def money_summary(
    tournament_id: UUID, supabase: SupabaseDep, admin: TournamentAdminDep
) -> MoneySummary:
    tid = str(tournament_id)
    ts.tournament(supabase, tid)
    ts.sweep(supabase, tid)
    money = rows(supabase.table(ts.MONEY).select("*").eq("tournament_id", tid).execute())
    all_teams = {str(t["id"]): t for t in ts.teams(supabase, tid)}
    names = {str(lv["id"]): str(lv["name"]) for lv in ts.levels(supabase, tid)}
    by_category: dict[str, float] = {}
    by_level: dict[str, float] = {}
    income = expense = 0.0
    for m in money:
        amount = float(m["amount"])
        if m["direction"] == "income":
            income += amount
        else:
            expense += amount
        by_category[m["category"]] = round(by_category.get(m["category"], 0.0) + amount, 2)
        if m["category"] == "entry_fee" and m.get("team_id") and str(m["team_id"]) in all_teams:
            name = names.get(str(all_teams[str(m["team_id"])]["level_id"]), "?")
            by_level[name] = round(by_level.get(name, 0.0) + amount, 2)
    ents = ts.entrants(supabase, tid)
    pending = [e for e in ents if e["pay_status"] == "slip_sent"]
    owed = [
        (e, ts.refund_owed(all_teams[str(e["team_id"])], e))
        for e in ents
        if str(e["team_id"]) in all_teams
    ]
    owed = [(e, amount) for e, amount in owed if amount]
    return MoneySummary(
        income=round(income, 2),
        expense=round(expense, 2),
        balance=round(income - expense, 2),
        by_category=by_category,
        by_level=by_level,
        pending_slips=len(pending),
        pending_amount=float(sum(int(e["share"]) for e in pending)),
        refunds_owed=len(owed),
        refunds_owed_amount=float(sum(amount for _, amount in owed)),
    )


# --- who runs it -------------------------------------------------------------


@router.get("/admins")
def tournament_admins(supabase: SupabaseDep, admin: TournamentAdminDep) -> list[dict[str, str]]:
    """Who may run tournaments, for the "paid by" of an expense."""
    found = rows(supabase.table("admins").select("id, username, tournament_access").execute())
    return sorted(
        (
            {"id": str(a["id"]), "username": str(a["username"])}
            for a in found
            if a.get("tournament_access")
        ),
        key=lambda a: a["username"],
    )


@router.get("/activity", response_model=list[AdminActivity])
def activity(
    supabase: SupabaseDep, admin: TournamentAdminDep, day: date | None = None
) -> list[AdminActivity]:
    """This side's own log: tournament writes only, never the club's."""
    query = (
        supabase.table("admin_activity_log")
        .select("*")
        .eq("area", "tournament")
        .order("created_at", desc=True)
        .limit(200)
    )
    if day is not None:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        query = query.gte("created_at", start.isoformat()).lt(
            "created_at", (start + timedelta(days=1)).isoformat()
        )
    names = {
        r["id"]: r["username"]
        for r in rows(supabase.table("admins").select("id, username").execute())
    }
    return [
        AdminActivity.model_validate({**r, "admin_username": names.get(r["admin_id"], "?")})
        for r in rows(query.execute())
    ]
