"""A member's own credit, from the /line page: the balance and its history,
and topping up — pick a package, pay its price by PromptPay, send the slip.
An admin checks the slip and approves it (routers/admin/credit_admin.py);
only then does the credit arrive. Who the member is comes from their LINE
token, never from the page."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, UploadFile, status
from supabase import Client

from app.db_utils import rows
from app.deps import LineMemberDep, SupabaseDep
from app.models.credit import CreditCard, CreditPackage, CreditTopup, LineCredit, TopupIn
from app.models.line import LineContext
from app.models.payment import PaymentInfoResponse
from app.routers.line import MAX_SLIP_BYTES, SLIP_MAX_PX, _member
from app.services import credit_card_service, credit_service, night_bill, payment_info_service
from app.services.image_service import resize_jpeg

router = APIRouter(prefix="/api/line/credit", tags=["line-credit"])


def _packages(supabase: Client) -> list[CreditPackage]:
    found = rows(supabase.table("credit_packages").select("*").eq("is_active", True).execute())
    found = [p for p in found if p.get("is_active")]
    found.sort(key=lambda p: (int(p.get("sort_order") or 0), int(p["credits"])))
    return [CreditPackage.model_validate(p) for p in found]


def _topups(supabase: Client, player_id: str) -> list[dict[str, Any]]:
    found = rows(
        supabase.table("credit_topups")
        .select("*")
        .eq("player_id", player_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    return sorted(
        (t for t in found if str(t["player_id"]) == player_id), key=lambda t: str(t["created_at"]), reverse=True
    )


def state(supabase: Client, member: LineContext) -> LineCredit:
    player = _member(supabase, member)
    pid = str(player.id)
    tops = _topups(supabase, pid)
    pending = next((t for t in tops if t["status"] == "pending"), None)
    latest_done = next((t for t in tops if t["status"] != "pending"), None)
    rejected = latest_done if latest_done and latest_done["status"] == "rejected" else None
    card = credit_card_service.all_cards(supabase).get(pid)
    return LineCredit(
        player=player,
        balance=credit_service.balance(supabase, pid),
        card=CreditCard(tier=card.tier, since=card.since) if card else None,
        packages=_packages(supabase),
        pending=CreditTopup.model_validate(pending) if pending else None,
        rejected=CreditTopup.model_validate(rejected) if rejected and not pending else None,
        history=credit_service.history(supabase, pid),
    )


def _own_pending(supabase: Client, member: LineContext, topup_id: UUID) -> dict[str, Any]:
    player = _member(supabase, member)
    found = rows(supabase.table("credit_topups").select("*").eq("id", str(topup_id)).limit(1).execute())
    # Someone else's top-up reads as not found, not as forbidden.
    if not found or str(found[0]["player_id"]) != str(player.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการเติมเครดิตนี้")
    if found[0]["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="รายการนี้แอดมินตรวจไปแล้ว")
    return found[0]


@router.get("", response_model=LineCredit)
def my_credit(supabase: SupabaseDep, member: LineMemberDep) -> LineCredit:
    return state(supabase, member)


@router.post("/topups", response_model=LineCredit)
def start_topup(payload: TopupIn, supabase: SupabaseDep, member: LineMemberDep) -> LineCredit:
    """Pick a package. One top-up waits at a time: picking another before
    sending a slip swaps the package; once a slip is sent, it waits for
    the admin."""
    player = _member(supabase, member)
    pid = str(player.id)
    package = next((p for p in _packages(supabase) if p.id == payload.package_id), None)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่มีแพ็กเกจนี้แล้ว — เลือกใหม่อีกครั้ง")
    pending = next((t for t in _topups(supabase, pid) if t["status"] == "pending"), None)
    if pending and pending.get("slip_url"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ส่งสลิปไปแล้ว รอแอดมินตรวจก่อนนะ แล้วค่อยเติมเพิ่ม"
        )
    if pending:
        supabase.table("credit_topups").update({"credits": package.credits, "price": package.price}).eq(
            "id", str(pending["id"])
        ).eq("status", "pending").execute()
    else:
        try:
            supabase.table("credit_topups").insert(
                {"player_id": pid, "credits": package.credits, "price": package.price}
            ).execute()
        except Exception as exc:  # the one-pending index: a double tap
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="มีรายการเติมเครดิตค้างอยู่แล้ว — รีเฟรชหน้า"
            ) from exc
    return state(supabase, member)


@router.get("/topups/{topup_id}/pay", response_model=PaymentInfoResponse)
def topup_pay_info(topup_id: UUID, supabase: SupabaseDep, member: LineMemberDep) -> PaymentInfoResponse:
    """The club's PromptPay QR with the package's price in it."""
    topup = _own_pending(supabase, member, topup_id)
    return payment_info_service.payment_info(supabase, float(topup["price"]))


@router.post("/topups/{topup_id}/slip", response_model=LineCredit)
async def topup_slip(
    topup_id: UUID, file: UploadFile, supabase: SupabaseDep, member: LineMemberDep
) -> LineCredit:
    """The slip of their transfer, for an admin to check. Sending again
    replaces the one they sent before."""
    topup = _own_pending(supabase, member, topup_id)
    contents = await file.read(MAX_SLIP_BYTES + 1)  # never more than one byte past the limit
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="รูปใหญ่เกินไป (ไม่เกิน 5MB)"
        )
    try:
        slip = resize_jpeg(contents, SLIP_MAX_PX)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์นี้ไม่ใช่รูปภาพ") from None
    path = f"credit-slip-{uuid4().hex}.jpg"
    bucket = supabase.storage.from_(night_bill.SLIP_BUCKET)
    bucket.upload(path, slip, {"content-type": "image/jpeg", "upsert": "false"})
    url = str(bucket.get_public_url(path))
    supabase.table("credit_topups").update(
        {"slip_url": url, "slip_sent_at": datetime.now(UTC).isoformat()}
    ).eq("id", str(topup_id)).eq("status", "pending").execute()
    night_bill.forget_slip(supabase, topup.get("slip_url"))
    return state(supabase, member)


@router.delete("/topups/{topup_id}", response_model=LineCredit)
def cancel_topup(topup_id: UUID, supabase: SupabaseDep, member: LineMemberDep) -> LineCredit:
    """Change their mind before the admin looks at it."""
    topup = _own_pending(supabase, member, topup_id)
    supabase.table("credit_topups").delete().eq("id", str(topup_id)).eq("status", "pending").execute()
    night_bill.forget_slip(supabase, topup.get("slip_url"))
    return state(supabase, member)
