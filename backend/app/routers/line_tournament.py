"""Signing up for a tournament from the /line page.

Anyone in the club's list who has played at least `min_games` games here
may sign up — a member or not — once their LINE is linked to their name.
Who they are comes from their LINE token, never from the page. Fees are
paid by transfer to the tournament's own account, never from club credit.
A team that has accepted can't pull out from here: only a tournament admin
withdraws a team (routers/admin/tournament.py).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile, status
from supabase import Client

from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import LineContext
from app.models.payment import PaymentInfoResponse
from app.models.tournament import (
    Candidate,
    Details,
    LineTournament,
    Me,
    RenameIn,
    SignUpIn,
)
from app.routers.line import MAX_SLIP_BYTES, SLIP_MAX_PX
from app.services import night_bill, promptpay_service, slip_check, tournament_cache
from app.services import tournament_service as ts
from app.services import tournament_views as views
from app.services.image_service import resize_jpeg

router = APIRouter(prefix="/api/line/tournament", tags=["line-tournament"])


def _player(supabase: Client, member: LineContext) -> dict[str, Any]:
    linked = rows(
        supabase.table("players")
        .select("*")
        .eq("line_user_id", member.line_user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not linked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="LINE นี้ยังไม่ได้ผูกกับชื่อในก๊วน")
    return linked[0]


def _current(supabase: Client) -> dict[str, Any]:
    row = ts.current(supabase)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ยังไม่มีทัวร์นาเมนต์ที่เปิดอยู่")
    ts.sweep(supabase, str(row["id"]))
    return row


def _open(row: dict[str, Any]) -> None:
    if not ts.taking_entries(row):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ตอนนี้ไม่ได้เปิดรับสมัคร")


def _entry(supabase: Client, row: dict[str, Any], player: dict[str, Any]) -> dict[str, Any]:
    entry = ts.active_entry(supabase, str(row["id"]), str(player["id"]))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="คุณยังไม่ได้อยู่ในทีมไหน")
    return entry


def _mine(
    supabase: Client, member: LineContext
) -> tuple[tournament_cache.Held | None, LineTournament]:
    """The tournament (from the short cache, else read in three round trips)
    alongside who this is, then the details they typed last time; and what
    is theirs alone — everything but the tournament itself."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        held_f = pool.submit(tournament_cache.current, supabase)
        player_f = pool.submit(_player, supabase, member)
        held = held_f.result()
        if held is None:
            return None, LineTournament(tournament=None)
        player = player_f.result()
    row, snap = held.row, held.snap
    pid = str(player["id"])
    details = ts.last_details(supabase, pid)
    own = ts.level_of(int(player.get("elo_score") or 0), snap.levels)
    me = Me(
        player_id=UUID(pid),
        nickname=player["nickname"],
        avatar_url=player.get("avatar_url"),
        elo=int(player.get("elo_score") or 0),
        elo_level=str(player.get("elo_level") or ""),
        games=int(player.get("games") or 0),
        games_needed=ts.games_needed(player, row),
        level_id=own["id"] if own else None,
    )
    entry = next((e for e in snap.entrants if str(e["player_id"]) == pid and e.get("active")), None)
    team = None
    if entry is not None:
        t = next((x for x in snap.teams if str(x["id"]) == str(entry["team_id"])), None)
        if t is not None:
            names = {str(lv["id"]): str(lv["name"]) for lv in snap.levels}
            ents = sorted(
                snap.by_team.get(str(t["id"]), []),
                key=lambda e: 0 if e["role"] == "captain" else 1,
            )
            team = views.team_model(t, ents, snap.players, names, show_private_of={pid})
    return held, LineTournament(
        tournament=None,
        me=me,
        team=team,
        my_role=entry["role"] if entry else None,
        last_details=Details.model_validate(details) if details else None,
    )


def state(supabase: Client, member: LineContext) -> LineTournament:
    """Everything the LINE page shows, as the reply to something they did."""
    held, mine = _mine(supabase, member)
    return mine.model_copy(update={"tournament": held.model(supabase) if held else None})


NO_TOURNAMENT = '{"tournament":null'


@router.get("", response_model=LineTournament)
def my_tournament(supabase: SupabaseDep, member: LineMemberDep) -> Response:
    """Polled by every open LINE page on the day: the tournament's JSON is
    the cached copy everyone shares, with this player's own part after it —
    the same reply `state` gives, without rebuilding the tournament."""
    held, mine = _mine(supabase, member)
    own = mine.model_dump_json()
    if held is None or not own.startswith(NO_TOURNAMENT):
        return Response(content=own, media_type="application/json")
    body = b'{"tournament":' + held.json(supabase) + own[len(NO_TOURNAMENT) :].encode()
    return Response(content=body, media_type="application/json")


@router.get("/candidates", response_model=list[Candidate])
def candidates(supabase: SupabaseDep, member: LineMemberDep) -> list[Candidate]:
    """Who this player could ask to be their partner: everyone in the list
    with LINE linked. Those who can't be picked yet come back marked, so the
    page can say why instead of hiding them."""
    row = _current(supabase)
    me = _player(supabase, member)
    taken = {str(e["player_id"]) for e in ts.entrants(supabase, str(row["id"])) if e.get("active")}
    found = rows(supabase.table("players").select("*").eq("is_active", True).execute())
    out = [
        Candidate(
            player_id=p["id"],
            nickname=p["nickname"],
            avatar_url=p.get("avatar_url"),
            elo=int(p.get("elo_score") or 0),
            elo_level=str(p.get("elo_level") or ""),
            games=int(p.get("games") or 0),
            eligible=ts.games_needed(p, row) == 0,
            taken=str(p["id"]) in taken,
        )
        for p in found
        if p.get("line_user_id") and str(p["id"]) != str(me["id"]) and p.get("is_active", True)
    ]
    return sorted(out, key=lambda c: c.nickname.lower())


@router.post("/team", response_model=LineTournament)
def sign_up(payload: SignUpIn, supabase: SupabaseDep, member: LineMemberDep) -> LineTournament:
    row = _current(supabase)
    _open(row)
    me = _player(supabase, member)
    partner = rows(
        supabase.table("players").select("*").eq("id", str(payload.partner_id)).limit(1).execute()
    )
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบคนที่เลือกเป็นคู่")
    lv = ts.check_pair(
        supabase, row, ts.Pair(me, partner[0]), str(payload.level_id), line_needed=True
    )
    details = {
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "phone": payload.phone,
    }
    ts.create_team(
        supabase, row, str(lv["id"]), payload.team_name, (me, details), (partner[0], None)
    )
    return state(supabase, member)


@router.post("/accept", response_model=LineTournament)
def accept(payload: Details, supabase: SupabaseDep, member: LineMemberDep) -> LineTournament:
    row = _current(supabase)
    _open(row)
    entry = _entry(supabase, row, _player(supabase, member))
    ts.accept(supabase, row, entry, payload.model_dump())
    return state(supabase, member)


@router.post("/decline", response_model=LineTournament)
def decline(supabase: SupabaseDep, member: LineMemberDep) -> LineTournament:
    """The partner says no, or the captain takes the invite back: either way
    nobody has paid yet, so nothing is owed."""
    row = _current(supabase)
    entry = _entry(supabase, row, _player(supabase, member))
    t = ts.team(supabase, str(entry["team_id"]))
    if t["status"] != "invited":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="คำชวนนี้ตอบไปแล้ว — ถ้าจะออก ใช้ปุ่มถอนตัว"
        )
    ts.end_team(supabase, t, "cancelled")
    return state(supabase, member)


@router.patch("/team", response_model=LineTournament)
def rename(payload: RenameIn, supabase: SupabaseDep, member: LineMemberDep) -> LineTournament:
    row = _current(supabase)
    _open(row)
    entry = _entry(supabase, row, _player(supabase, member))
    t = ts.team(supabase, str(entry["team_id"]))
    supabase.table(ts.TEAMS).update({"name": payload.team_name}).eq("id", str(t["id"])).execute()
    return state(supabase, member)


@router.get("/pay", response_model=PaymentInfoResponse)
def pay_info(
    supabase: SupabaseDep, member: LineMemberDep, team: bool = False
) -> PaymentInfoResponse:
    """The tournament's own PromptPay QR with this player's share in it, or
    (`team`) both shares, to pay for their partner too. Each share keeps its
    own Niddeaw Pass discount."""
    row = _current(supabase)
    entry = _entry(supabase, row, _player(supabase, member))
    lowered = ts.take_pass_off(supabase, entry)
    changed = lowered is not entry
    entry = lowered
    shares = [entry]
    if team:
        partner = ts.teammate(supabase, entry)
        if not ts.can_cover(entry, partner) or partner is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="คู่ของคุณจ่ายหรือส่งสลิปส่วนของเขาไปแล้ว จ่ายได้แค่ส่วนของตัวเอง",
            )
        theirs = ts.take_pass_off(supabase, partner)
        changed = changed or theirs is not partner
        shares.append(theirs)
    if changed:
        tournament_cache.invalidate()
    if not row.get("promptpay_id") or not row.get("promptpay_type"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ผู้จัดยังไม่ได้ตั้งบัญชีรับเงินของงาน"
        )
    amount = float(sum(int(e["share"]) for e in shares))
    payload = promptpay_service.build_promptpay_payload(
        row["promptpay_id"], row["promptpay_type"], amount
    )
    return PaymentInfoResponse(
        method="promptpay",
        amount=amount,
        data_uri=promptpay_service.generate_qr_data_uri(payload),
        qr_modules=promptpay_service.qr_modules(payload),
        # Typed into a banking app by those who'd rather not scan.
        bank_name="PromptPay",
        bank_account_number=row["promptpay_id"],
        bank_account_name=row.get("account_name"),
    )


@router.post("/slip", response_model=LineTournament)
async def send_slip(
    file: UploadFile, supabase: SupabaseDep, member: LineMemberDep, for_team: bool = Form(False)
) -> LineTournament:
    """`for_team`: the slip pays the partner's share too."""
    row = _current(supabase)
    entry = _entry(supabase, row, _player(supabase, member))
    contents = await file.read(MAX_SLIP_BYTES + 1)
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="รูปใหญ่เกินไป (ไม่เกิน 5MB)"
        )
    try:
        image = resize_jpeg(contents, SLIP_MAX_PX)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์นี้ไม่ใช่รูปภาพ"
        ) from None
    path = f"tournament-slip-{uuid4().hex}.jpg"
    bucket = supabase.storage.from_(night_bill.SLIP_BUCKET)
    bucket.upload(path, image, {"content-type": "image/jpeg", "upsert": "false"})
    url = str(bucket.get_public_url(path))
    ts.record_slip(supabase, entry, url, for_team=for_team)
    slip_check.record(supabase, "tournament", str(entry["id"]), url, contents, image)
    return state(supabase, member)
