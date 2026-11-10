"""The admin's side of club credit: checking top-up slips, members'
balances and their history, adjusting a balance (cash taken at the court,
a refund, a correction — always with a reason), and the packages on sale."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import ValidationError

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.credit import (
    CreditAdjust,
    CreditBalances,
    CreditPackage,
    CreditPackageIn,
    CreditPackageUpdate,
    CreditSummary,
    CreditTopupAdmin,
    MemberCredit,
    MemberLedger,
    TopupReject,
)
from app.models.player import Player
from app.services import credit_service

router = APIRouter(prefix="/api/admin/credit", tags=["admin-credit"])


def _players(supabase: SupabaseDep, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    found = rows(supabase.table("players").select("id, nickname, member_seq").in_("id", ids).execute())
    return {str(p["id"]): p for p in found}


def _code(p: dict[str, Any] | None) -> str:
    return f"ND{int(p['member_seq']):03d}" if p and p.get("member_seq") is not None else ""


def _with_names(supabase: SupabaseDep, topups: list[dict[str, Any]]) -> list[CreditTopupAdmin]:
    names = _players(supabase, list({str(t["player_id"]) for t in topups}))
    return [
        CreditTopupAdmin.model_validate(
            {
                **t,
                "player_nickname": (names.get(str(t["player_id"])) or {}).get("nickname", "?"),
                "player_code": _code(names.get(str(t["player_id"]))),
            }
        )
        for t in topups
    ]


@router.get("/topups", response_model=list[CreditTopupAdmin])
def list_topups(
    supabase: SupabaseDep,
    admin: AdminDep,
    which: Annotated[str, Query(pattern="^(waiting|done)$")] = "waiting",
) -> list[CreditTopupAdmin]:
    """waiting: slips sent and not yet checked, oldest first. done: the
    latest decisions."""
    if which == "waiting":
        found = rows(supabase.table("credit_topups").select("*").eq("status", "pending").order("created_at").execute())
        found = [t for t in found if t["status"] == "pending" and t.get("slip_url")]
        found.sort(key=lambda t: str(t.get("slip_sent_at") or t["created_at"]))
    else:
        found = rows(
            supabase.table("credit_topups")
            .select("*")
            .neq("status", "pending")
            .order("decided_at", desc=True)
            .limit(30)
            .execute()
        )
        found = sorted((t for t in found if t["status"] != "pending"), key=lambda t: str(t.get("decided_at")), reverse=True)
    return _with_names(supabase, found)


@router.post("/topups/{topup_id}/approve", response_model=CreditTopupAdmin)
def approve_topup(topup_id: UUID, request: Request, supabase: SupabaseDep, admin: AdminDep) -> CreditTopupAdmin:
    topup = credit_service.approve_topup(supabase, topup_id, admin.admin_id)
    done = _with_names(supabase, [topup])[0]
    request.state.activity_detail = {"member": done.player_nickname, "credits": done.credits, "paid": done.price}
    return done


@router.post("/topups/{topup_id}/reject", response_model=CreditTopupAdmin)
def reject_topup(
    topup_id: UUID, payload: TopupReject, request: Request, supabase: SupabaseDep, admin: AdminDep
) -> CreditTopupAdmin:
    """The slip doesn't match: nothing is credited, and the member sees
    why in LINE and can top up again."""
    updated = rows(
        supabase.table("credit_topups")
        .update(
            {
                "status": "rejected",
                "decided_at": datetime.now(UTC).isoformat(),
                "note": payload.note or "สลิปไม่ตรงกับยอดที่ต้องโอน",
            }
        )
        .eq("id", str(topup_id))
        .eq("status", "pending")
        .execute()
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="รายการนี้ตรวจไปแล้ว — รีเฟรชหน้า")
    done = _with_names(supabase, updated)[0]
    request.state.activity_detail = {"member": done.player_nickname, "credits": done.credits}
    return done


@router.get("/balances", response_model=CreditBalances)
def balances(supabase: SupabaseDep, admin: AdminDep) -> CreditBalances:
    """Every member who has or had credit, most first."""
    found = credit_service.all_rows(supabase, "player_credits", "player_id, balance", key="player_id")
    names = _players(supabase, [str(b["player_id"]) for b in found])
    members = sorted(
        (
            MemberCredit(
                player_id=b["player_id"],
                nickname=(names.get(str(b["player_id"])) or {}).get("nickname", "?"),
                member_code=_code(names.get(str(b["player_id"]))),
                balance=int(b["balance"]),
            )
            for b in found
        ),
        key=lambda m: (-m.balance, m.nickname.lower()),
    )
    return CreditBalances(outstanding=sum(m.balance for m in members), members=members)


def _player(supabase: SupabaseDep, player_id: UUID) -> Player:
    found = rows(supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(found[0])


@router.get("/players/{player_id}", response_model=MemberLedger)
def member_ledger(player_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> MemberLedger:
    return MemberLedger(
        player=_player(supabase, player_id),
        balance=credit_service.balance(supabase, player_id),
        history=credit_service.history(supabase, player_id, limit=100),
    )


@router.post("/players/{player_id}/adjust", response_model=MemberLedger)
def adjust(
    player_id: UUID, payload: CreditAdjust, request: Request, supabase: SupabaseDep, admin: AdminDep
) -> MemberLedger:
    player = _player(supabase, player_id)
    try:
        credit_service.apply(
            supabase,
            player_id,
            payload.delta,
            "adjust",
            cash=payload.cash,
            note=payload.note,
            admin_id=admin.admin_id,
        )
    except credit_service.NotEnoughCredit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ลดได้ไม่เกินที่มี ({credit_service.balance(supabase, player_id):,} เครดิต)",
        ) from None
    request.state.activity_detail = {
        "member": player.nickname,
        "delta": payload.delta,
        "cash": payload.cash,
        "note": payload.note,
    }
    return member_ledger(player_id, supabase, admin)


@router.get("/packages", response_model=list[CreditPackage])
def list_packages(supabase: SupabaseDep, admin: AdminDep) -> list[CreditPackage]:
    found = rows(supabase.table("credit_packages").select("*").execute())
    # cheapest first, the club's ask; at the same price the bigger pack first.
    # sort_order is never set by hand, so it plays no part.
    found.sort(key=lambda p: (float(p["price"]), -int(p["credits"])))
    return [CreditPackage.model_validate(p) for p in found]


@router.post("/packages", response_model=CreditPackage, status_code=status.HTTP_201_CREATED)
def create_package(payload: CreditPackageIn, supabase: SupabaseDep, admin: AdminDep) -> CreditPackage:
    created = rows(supabase.table("credit_packages").insert(payload.model_dump()).execute())
    return CreditPackage.model_validate(created[0])


@router.patch("/packages/{package_id}", response_model=CreditPackage)
def update_package(
    package_id: UUID, payload: CreditPackageUpdate, supabase: SupabaseDep, admin: AdminDep
) -> CreditPackage:
    found = rows(supabase.table("credit_packages").select("*").eq("id", str(package_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบแพ็กเกจนี้")
    updates = payload.model_dump(exclude_unset=True)
    merged = {**found[0], **updates}
    # The same rule as a new package, checked on the result.
    try:
        CreditPackageIn.model_validate(
            {k: merged[k] for k in ("credits", "price", "is_active", "sort_order")}
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="ราคาต้องไม่เกินจำนวนเครดิตที่ได้"
        ) from exc
    if not updates:
        return CreditPackage.model_validate(found[0])
    updated = rows(supabase.table("credit_packages").update(updates).eq("id", str(package_id)).execute())
    return CreditPackage.model_validate(updated[0])


@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Gone from sale. Top-ups already made keep their own copy of what
    was bought, so nothing else changes."""
    supabase.table("credit_packages").delete().eq("id", str(package_id)).execute()


@router.get("/summary", response_model=CreditSummary)
def summary(supabase: SupabaseDep, admin: AdminDep) -> CreditSummary:
    return credit_service.summary(supabase)
