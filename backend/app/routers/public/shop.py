import uuid
from collections import deque
from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request, UploadFile, status

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.payment import PaymentInfoResponse
from app.models.shop import ONE_SIZE, OrderPublic, Product
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


@router.get("/products/{product_id}/payment", response_model=PaymentInfoResponse)
def payment_for(
    product_id: UUID, supabase: SupabaseDep, qty: Annotated[int, Query(ge=1, le=10)]
) -> PaymentInfoResponse:
    """How to pay for `qty` of this product: the club's PromptPay QR with
    the total in it (or whatever method Settings has). The total comes from
    the product's price here, never from the page."""
    product = _product_row(supabase, product_id)
    return payment_info_service.payment_info(supabase, round(float(str(product["price"])) * qty, 2))


@router.post("/orders", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
async def place_order(
    request: Request,
    supabase: SupabaseDep,
    file: UploadFile,
    product_id: Annotated[UUID, Form()],
    player_id: Annotated[UUID, Form()],
    qty: Annotated[int, Form(ge=1, le=10)],
    size: Annotated[str, Form()] = ONE_SIZE,
) -> OrderPublic:
    """A member's order, with the slip of the transfer they have just made.
    It waits as 'pending' until an admin checks the slip."""
    _throttle(request)
    product = shop_service.hydrate(supabase, [_product_row(supabase, product_id)])[0]
    size = size.strip()
    sizes: list[str] = list(product["sizes"])
    if sizes and size not in sizes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="เลือกไซซ์ก่อน")
    if not sizes:
        size = ONE_SIZE

    member = (
        supabase.table("players").select("id, is_active").eq("id", str(player_id)).limit(1).execute()
    )
    member_rows = rows(member)
    if not member_rows or not member_rows[0].get("is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่พบชื่อสมาชิกนี้ในก๊วน")

    if product["sale_type"] == "preorder" and not product["open"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="พรีออเดอร์นี้ปิดรับแล้ว")

    contents = await file.read()
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Slip file too large (max 5MB)"
        )
    try:
        slip = resize_jpeg(contents, SLIP_MAX_PX)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type") from None

    took = False
    if product["sale_type"] == "stock":
        took = shop_service.take(supabase, str(product_id), size, qty)
        if not took:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ของหมดพอดี — เหลือไม่พอตามจำนวนที่สั่ง ลองลดจำนวนหรือเลือกไซซ์อื่น",
            )

    path = f"slip-{uuid.uuid4().hex}.jpg"
    try:
        bucket = supabase.storage.from_(SHOP_BUCKET)
        bucket.upload(path, slip, {"content-type": "image/jpeg", "upsert": "false"})
        slip_url: str = bucket.get_public_url(path)
        unit_price = round(float(str(product["price"])), 2)
        result = (
            supabase.table("shop_orders")
            .insert(
                {
                    "player_id": str(player_id),
                    "product_id": str(product_id),
                    "product_name": product["name"],
                    "sale_type": product["sale_type"],
                    "size": size,
                    "qty": qty,
                    "unit_price": unit_price,
                    "total": round(unit_price * qty, 2),
                    "slip_url": slip_url,
                }
            )
            .execute()
        )
    except Exception:
        # The shirt goes back on the shelf if the order didn't get written.
        if took:
            shop_service.give_back(supabase, str(product_id), size, qty)
        raise
    return OrderPublic.model_validate(rows(result)[0])


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
    return [OrderPublic.model_validate(r) for r in rows(result)]
