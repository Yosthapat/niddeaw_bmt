"""Niddeaw Pass in LINE: see it, buy it with credit, and choose tonight's
two members not to be partnered with (pass_service). Only the member's own
LINE token reaches these; nobody else, admins included, sees the choices."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter
from supabase import Client

from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.line import LineContext
from app.models.niddeaw_pass import LinePass, PassBlockIn, PassPerson
from app.routers.line import _member
from app.services import credit_service, pass_service

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
    return LinePass(
        price=pass_service.price(supabase),
        days=pass_service.PASS_DAYS,
        balance=credit_service.balance(supabase, pid),
        eligible=pass_service.eligible(supabase, pid),
        ends_at=pass_service.runs_until(supabase, pid, now),
        max_blocks=pass_service.BLOCKS_PER_NIGHT,
        checked_in=night is not None,
        blocks=_people(supabase, blocks),
        candidates=_people(supabase, others),
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
