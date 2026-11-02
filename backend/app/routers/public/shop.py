import contextlib
import json
import uuid
from collections import deque
from time import monotonic
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.payment import PaymentInfoResponse
from app.models.shop import (
    MAX_LINE_QTY,
    ONE_SIZE,
    Cart,
    OrderPublic,
    Product,
    Quote,
    QuoteLine,
    unit_price,
)
from app.services import login_throttle, payment_info_service, shop_service
from app.services.image_service import resize_jpeg

router = APIRouter(prefix="/api/shop", tags=["public-shop"])

SHOP_BUCKET = "shop"
MAX_SLIP_BYTES = 5 * 1024 * 1024  # 5MB — same as receipts
SLIP_MAX_PX = 1600  # a slip is read back for its small print; keep it legible

# Anyone can place an order — members have no accounts — so the endpoint is
# the one public write in the app. A member orders a shirt or two; a script
# filling the bucket with slips is what this stops.
ORDERS_PER_WINDOW = 10
ORDER_WINDOW_SECONDS = 60 * 60
_recent_orders: dict[str, deque[float]] = {}


def _throttle(request: Request) -> None:
    key = login_throttle.client_key(
        request.headers.get("x-forwarded-for"), request.client.host if request.client else None
    )
    now = monotonic()
    stamps = _recent_orders.setdefault(key, deque())
    while stamps and now - stamps[0] >= ORDER_WINDOW_SECONDS:
        stamps.popleft()
    if len(stamps) >= ORDERS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="สั่งบ่อยเกินไป ลองใหม่อีกครั้งในอีกสักพัก",
        )
    stamps.append(now)


def reset_throttle() -> None:
    _recent_orders.clear()


def _product_row(supabase: SupabaseDep, product_id: UUID) -> dict[str, object]:
    result = supabase.table("products").select("*").eq("id", str(product_id)).limit(1).execute()
    found = rows(result)
    if not found or not found[0].get("is_active"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return found[0]


@router.get("/products", response_model=list[Product])
def list_products(supabase: SupabaseDep) -> list[Product]:
    result = (
        supabase.table("products")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .order("created_at", desc=True)
        .execute()
    )
    return [Product.model_validate(p) for p in shop_service.hydrate(supabase, rows(result))]


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: UUID, supabase: SupabaseDep) -> Product:
    return Product.model_validate(shop_service.hydrate(supabase, [_product_row(supabase, product_id)])[0])


def build_quote(supabase: SupabaseDep, cart: Cart) -> Quote:
    """Price a cart from the products as they are now, and say of each line
    whether it can still be bought — the cart page draws this, and placing
    the order trusts nothing else. The same product and size twice is one
    line."""
    merged: dict[tuple[str, str], int] = {}
    for line in cart.items:
        key = (str(line.product_id), line.size)
        merged[key] = merged.get(key, 0) + line.qty
    ids = sorted({pid for pid, _ in merged})
    result = supabase.table("products").select("*").in_("id", ids).execute()
    found = {str(p["id"]): p for p in shop_service.hydrate(supabase, [r for r in rows(result) if str(r["id"]) in ids])}
    lines: list[QuoteLine] = []
    for (pid, size), qty in merged.items():
        product = found.get(pid)
        if product is None or not product.get("is_active"):
            lines.append(
                QuoteLine(
                    product_id=UUID(pid), product_name="สินค้านี้", sale_type="stock", size=size, qty=qty,
                    unit_price=0, line_total=0, problem="ไม่ขายแล้ว — เอาออกจากตะกร้า",
                )
            )
            continue
        sizes: list[str] = list(product["sizes"])
        if not sizes:
            size = ONE_SIZE
        price = unit_price(product, size)
        problem: str | None = None
        available: int | None = None
        if sizes and size not in sizes:
            problem = "ไม่มีไซส์นี้แล้ว — เลือกใหม่"
        elif qty > MAX_LINE_QTY:
            problem = f"สั่งได้สูงสุด {MAX_LINE_QTY} ตัวต่อไซส์"
        elif product["sale_type"] == "preorder":
            if not product["open"]:
                problem = "ปิดรับพรีออเดอร์แล้ว"
        else:
            available = int(product["stock"].get(size, 0))
            if available < 1:
                problem = "หมดแล้ว"
            elif available < qty:
                problem = f"เหลือแค่ {available} ตัว"
        images: list[str] = list(product.get("image_urls") or [])
        lines.append(
            QuoteLine(
                product_id=UUID(pid), product_name=product["name"], image_url=images[0] if images else None,
                sale_type=product["sale_type"], size=size, qty=qty, unit_price=price,
                line_total=round(price * qty, 2), problem=problem, available=available,
            )
        )
    return Quote(
        lines=lines,
        total=round(sum(line.line_total for line in lines if not line.problem), 2),
        ok=all(line.problem is None for line in lines),
    )


@router.post("/quote", response_model=Quote)
def quote(cart: Cart, supabase: SupabaseDep) -> Quote:
    return build_quote(supabase, cart)


@router.post("/payment", response_model=PaymentInfoResponse)
def payment_for(cart: Cart, supabase: SupabaseDep) -> PaymentInfoResponse:
    """How to pay for this cart: the club's PromptPay QR with the total in
    it (or whatever method Settings has). The total comes from the products'
    prices here, never from the page."""
    priced = build_quote(supabase, cart)
    if not priced.ok:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_first_problem(priced))
    return payment_info_service.payment_info(supabase, priced.total)


def _first_problem(priced: Quote) -> str:
    line = next(line for line in priced.lines if line.problem)
    label = f"{line.product_name} {line.size}".strip()
    return f"{label}: {line.problem}"


@router.post("/orders", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
async def place_order(
    request: Request,
    supabase: SupabaseDep,
    file: UploadFile,
    player_id: Annotated[UUID, Form()],
    items: Annotated[str, Form(max_length=4000)],
) -> OrderPublic:
    """A member's whole cart as one order, with the slip of the one transfer
    they have just made. It waits as 'pending' until an admin checks it."""
    _throttle(request)
    try:
        cart = Cart.model_validate({"items": json.loads(items)})
    except (ValueError, ValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ตะกร้าว่าง หรือข้อมูลไม่ถูกต้อง") from None
    priced = build_quote(supabase, cart)
    if not priced.ok:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_first_problem(priced))

    member = (
        supabase.table("players").select("id, is_active").eq("id", str(player_id)).limit(1).execute()
    )
    member_rows = rows(member)
    if not member_rows or not member_rows[0].get("is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่พบชื่อสมาชิกนี้ในก๊วน")

    contents = await file.read()
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Slip file too large (max 5MB)"
        )
    try:
        slip = resize_jpeg(contents, SLIP_MAX_PX)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type") from None

    lines: list[dict[str, Any]] = [
        {
            "product_id": str(line.product_id), "product_name": line.product_name, "sale_type": line.sale_type,
            "size": line.size, "qty": line.qty, "unit_price": line.unit_price, "line_total": line.line_total,
        }
        for line in priced.lines
    ]
    # Someone may have bought the last one since the quote above.
    short = shop_service.take_lines(supabase, lines)
    if short is not None:
        label = f"{short['product_name']} {short['size']}".strip()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{label}: ของหมดพอดี — เหลือไม่พอตามจำนวนที่สั่ง ลองลดจำนวนหรือเลือกไซส์อื่น",
        )

    order_id: str | None = None
    try:
        path = f"slip-{uuid.uuid4().hex}.jpg"
        bucket = supabase.storage.from_(SHOP_BUCKET)
        bucket.upload(path, slip, {"content-type": "image/jpeg", "upsert": "false"})
        slip_url: str = bucket.get_public_url(path)
        order = rows(
            supabase.table("shop_orders")
            .insert({"player_id": str(player_id), "total": priced.total, "slip_url": slip_url})
            .execute()
        )[0]
        order_id = str(order["id"])
        saved = rows(
            supabase.table("shop_order_items").insert([{**line, "order_id": order_id} for line in lines]).execute()
        )
    except Exception:
        # The shirts go back on the shelf if the order didn't get written.
        shop_service.give_back_lines(supabase, lines)
        if order_id:
            with contextlib.suppress(Exception):
                supabase.table("shop_orders").delete().eq("id", order_id).execute()
        raise
    return OrderPublic.model_validate({**order, "items": saved})


@router.get("/orders", response_model=list[OrderPublic])
def orders_of(player_id: UUID, supabase: SupabaseDep) -> list[OrderPublic]:
    """A member's own orders and where each one is, for their profile."""
    result = (
        supabase.table("shop_orders")
        .select("*")
        .eq("player_id", str(player_id))
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    mine = [r for r in rows(result) if str(r.get("player_id")) == str(player_id)]
    return [OrderPublic.model_validate(o) for o in shop_service.with_items(supabase, mine)]
