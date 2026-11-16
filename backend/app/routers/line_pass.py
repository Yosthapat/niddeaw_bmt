"""Niddeaw Pass in LINE: see it, buy it with credit, and choose tonight's
two members not to be partnered with (pass_service). Only the member's own
LINE token reaches these; nobody else, admins included, sees the choices."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import LineContext
from app.models.niddeaw_pass import (
    LinePass,
    PassBlockIn,
    PassMate,
    PassNight,
    PassPerson,
    PassStats,
    PassStyleIn,
    PassUpset,
)
from app.routers.line import _member
from app.services import credit_service, pass_perks, pass_service

router = APIRouter(prefix="/api/line/pass", tags=["line-pass"])


def _people(supabase: Client, ids: list[str]) -> list[PassPerson]:
    if not ids:
        return []
    found = {
        str(p["id"]): p
        for p in rows(supabase.table("players").select("id,nickname,avatar_url").in_("id", ids).execute())
    }
    people = [
        PassPerson(player_id=UUID(i), nickname=found[i]["nickname"], avatar_url=found[i].get("avatar_url"))
        for i in ids
        if i in found
    ]
    return sorted(people, key=lambda p: p.nickname.lower())


def state(supabase: Client, member: LineContext) -> LinePass:
    player = _member(supabase, member)
    pid = str(player.id)
    now = datetime.now(UTC)
    night = pass_service.night_of(supabase, pid)
    blocks: list[str] = []
    others: list[str] = []
    if night is not None:
        blocks = pass_service.blocks_of(supabase, night["id"], pid)
        others = [p for p in pass_service.checked_in(supabase, night["id"]) if p != pid and p not in blocks]
    ends_at = pass_service.runs_until(supabase, pid, now)
    run = pass_perks.streak_of(pass_service.passes_of(supabase, pid), now)
    frames_open, cards_open = pass_perks.allowed(ends_at is not None, run.best)
    style = pass_perks.style_of(supabase, pid)
    return LinePass(
        price=pass_service.price(supabase),
        days=pass_service.PASS_DAYS,
        balance=credit_service.balance(supabase, pid),
        eligible=pass_service.eligible(supabase, pid),
        ends_at=ends_at,
        max_blocks=pass_service.BLOCKS_PER_NIGHT,
        checked_in=night is not None,
        blocks=_people(supabase, blocks),
        candidates=_people(supabase, others),
        frame=style["frame"],
        card=style["card"],
        frames_open=frames_open,
        cards_open=cards_open,
        streak=run.current,
        best_streak=run.best,
    )


@router.get("", response_model=LinePass)
def my_pass(supabase: SupabaseDep, member: LineMemberDep) -> LinePass:
    return state(supabase, member)


@router.post("/buy", response_model=LinePass)
def buy(supabase: SupabaseDep, member: LineMemberDep) -> LinePass:
    """Pay the price in credit for PASS_DAYS more days."""
    pass_service.buy(supabase, _member(supabase, member).id)
    return state(supabase, member)


@router.post("/blocks", response_model=LinePass)
def add_block(payload: PassBlockIn, supabase: SupabaseDep, member: LineMemberDep) -> LinePass:
    pass_service.block(supabase, _member(supabase, member).id, payload.player_id)
    return state(supabase, member)


@router.delete("/blocks/{player_id}", response_model=LinePass)
def remove_block(player_id: UUID, supabase: SupabaseDep, member: LineMemberDep) -> LinePass:
    pass_service.unblock(supabase, _member(supabase, member).id, player_id)
    return state(supabase, member)


@router.put("/style", response_model=LinePass)
def set_style(payload: PassStyleIn, supabase: SupabaseDep, member: LineMemberDep) -> LinePass:
    """The frame round their picture and their card's face; None for none."""
    pass_perks.set_style(supabase, _member(supabase, member).id, payload.frame, payload.card)
    return state(supabase, member)


def _holder(supabase: Client, member: LineContext) -> str:
    pid = str(_member(supabase, member).id)
    if pass_service.runs_until(supabase, pid) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ใช้ได้ระหว่างที่ Pass ยังไม่หมดอายุ")
    return pid


def _mate(supabase: Client, found: dict[str, Any] | None) -> PassMate | None:
    if not found:
        return None
    people = _people(supabase, [found["player_id"]])
    return PassMate(player=people[0], wins=found["wins"], games=found["games"]) if people else None


@router.get("/stats", response_model=PassStats)
def my_stats(supabase: SupabaseDep, member: LineMemberDep) -> PassStats:
    numbers = pass_perks.stats(supabase, _holder(supabase, member))
    return PassStats(
        **{k: v for k, v in numbers.items() if k not in ("partner", "rival")},
        partner=_mate(supabase, numbers["partner"]),
        rival=_mate(supabase, numbers["rival"]),
    )


@router.get("/night", response_model=PassNight | None)
def my_night(supabase: SupabaseDep, member: LineMemberDep) -> PassNight | None:
    """Their last night with a result; None before their first."""
    pid = _holder(supabase, member)
    found = pass_perks.night(supabase, pid)
    if found is None:
        return None
    player = _member(supabase, member)
    upset = found["upset"]
    return PassNight(
        **{k: v for k, v in found.items() if k not in ("upset", "partner")},
        nickname=player.nickname,
        frame=pass_perks.looks(supabase).get(pid, {}).get("frame"),
        upset=PassUpset(rivals=_people(supabase, upset["rival_ids"]), odds=upset["odds"]) if upset else None,
        partner=_mate(supabase, found["partner"]),
    )
