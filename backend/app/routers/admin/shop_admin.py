import contextlib
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.shop import (
    MAX_IMAGES,
    ONE_SIZE,
    OrderAdmin,
    OrderStatus,
    OrderUpdate,
    PreorderTally,
    Product,
    ProductCreate,
    ProductFields,
)
from app.services import shop_service
from app.services.image_service import resize_jpeg, storage_path_from_url

router = APIRouter(prefix="/api/admin/shop", tags=["admin-shop"])

SHOP_BUCKET = "shop"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Drawn at most ~420 CSS px wide on a product page; twice that for retina.
IMAGE_MAX_PX = 900
IMAGE_CACHE_SECONDS = "31536000"  # random object names, so a year is safe


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _check(merged: dict[str, Any], stock: dict[str, int] | None) -> None:
    """The rules that span fields: a pre-order needs its closing date, and
    stock must be given for exactly the sizes the product has."""
    if merged["sale_type"] == "preorder":
        if not merged.get("preorder_closes_on"):
            raise _bad("พรีออเดอร์ต้องมีวันปิดรับ")
        closes, delivers = merged.get("preorder_closes_on"), merged.get("preorder_delivers_on")
        if closes and delivers and str(delivers) < str(closes):
            raise _bad("วันได้ของต้องไม่ก่อนวันปิดรับ")
    if stock is not None and merged["sale_type"] == "stock":
        expected = set(merged["sizes"]) or {ONE_SIZE}
        if set(stock) != expected:
            raise _bad("ใส่จำนวนสต็อกให้ครบทุกไซซ์")


def _write_stock(supabase: SupabaseDep, product_id: str, stock: dict[str, int]) -> None:
    current = supabase.table("product_stock").select("size").eq("product_id", product_id).execute()
    gone = [r["size"] for r in rows(current) if r["size"] not in stock]
    for size in gone:
        supabase.table("product_stock").delete().eq("product_id", product_id).eq("size", size).execute()
    if stock:
        supabase.table("product_stock").upsert(
            [{"product_id": product_id, "size": size, "qty": qty} for size, qty in stock.items()],
            on_conflict="product_id,size",
        ).execute()


def _product(supabase: SupabaseDep, product_id: str) -> dict[str, Any]:
    result = supabase.table("products").select("*").eq("id", product_id).limit(1).execute()
    found = rows(result)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return found[0]


def _hydrated(supabase: SupabaseDep, row: dict[str, Any]) -> Product:
    return Product.model_validate(shop_service.hydrate(supabase, [row])[0])


# ---------------------------------------------------------------- products


@router.get("/products", response_model=list[Product])
def list_products(supabase: SupabaseDep, admin: AdminDep) -> list[Product]:
    result = supabase.table("products").select("*").order("sort_order").order("created_at", desc=True).execute()
    return [Product.model_validate(p) for p in shop_service.hydrate(supabase, rows(result))]


@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, supabase: SupabaseDep, admin: AdminDep) -> Product:
    fields = payload.model_dump(mode="json", exclude={"stock"}, exclude_none=True)
    fields.setdefault("sizes", [])
    if payload.sale_type == "stock" and payload.stock is None:
        raise _bad("ใส่จำนวนสต็อกให้ครบทุกไซซ์")
    _check(fields, payload.stock)
    if fields["sale_type"] == "stock":
        fields.pop("preorder_closes_on", None)
        fields.pop("preorder_delivers_on", None)
    result = supabase.table("products").insert(fields).execute()
    row = rows(result)[0]
    if payload.sale_type == "stock" and payload.stock is not None:
        _write_stock(supabase, str(row["id"]), payload.stock)
    return _hydrated(supabase, row)


@router.patch("/products/{product_id}", response_model=Product)
def update_product(
    product_id: UUID, payload: ProductFields, supabase: SupabaseDep, admin: AdminDep
) -> Product:
    current = _product(supabase, str(product_id))
    updates = payload.model_dump(mode="json", exclude_unset=True, exclude={"stock"})
    merged = {**current, **updates}
    _check(merged, payload.stock)
    if not updates and payload.stock is None:
        raise _bad("No fields to update")
    if updates:
        result = supabase.table("products").update(updates).eq("id", str(product_id)).execute()
        current = rows(result)[0]
    if merged["sale_type"] == "stock" and payload.stock is not None:
        _write_stock(supabase, str(product_id), payload.stock)
    elif merged["sale_type"] == "preorder":
        # A product switched to pre-order has no shelf any more.
        _write_stock(supabase, str(product_id), {})
    return _hydrated(supabase, current)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Deleting is for a product added by mistake. One that has orders keeps
    its history: stop selling it (is_active) instead."""
    product = _product(supabase, str(product_id))
    orders = supabase.table("shop_orders").select("id").eq("product_id", str(product_id)).limit(1).execute()
    if rows(orders):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="สินค้านี้มีออเดอร์แล้ว ลบไม่ได้ — ปิด \"ขายอยู่\" แทน",
        )
    supabase.table("products").delete().eq("id", str(product_id)).execute()
    for url in product.get("image_urls") or []:
        _forget(supabase, url)


def _forget(supabase: SupabaseDep, url: str) -> None:
    """Remove a photo nothing points at any more. Best effort."""
    path = storage_path_from_url(url, SHOP_BUCKET)
    if path:
        with contextlib.suppress(Exception):
            supabase.storage.from_(SHOP_BUCKET).remove([path])


@router.post("/products/{product_id}/images", response_model=Product)
async def add_image(
    product_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> Product:
    product = _product(supabase, str(product_id))
    urls: list[str] = list(product.get("image_urls") or [])
    if len(urls) >= MAX_IMAGES:
        raise _bad(f"ใส่รูปได้สูงสุด {MAX_IMAGES} รูป — ลบรูปเก่าก่อน")
    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image file too large (max 5MB)"
        )
    try:
        image = resize_jpeg(contents, IMAGE_MAX_PX)
    except ValueError:
        raise _bad("Unsupported image type") from None
    # flat and random: storage_path_from_url reads it back for deleting
    path = f"product-{uuid.uuid4().hex}.jpg"
    bucket = supabase.storage.from_(SHOP_BUCKET)
    bucket.upload(path, image, {"content-type": "image/jpeg", "cache-control": IMAGE_CACHE_SECONDS})
    url: str = bucket.get_public_url(path)
    result = (
        supabase.table("products").update({"image_urls": [*urls, url]}).eq("id", str(product_id)).execute()
    )
    return _hydrated(supabase, rows(result)[0])


@router.delete("/products/{product_id}/images", response_model=Product)
def remove_image(
    product_id: UUID, supabase: SupabaseDep, admin: AdminDep, url: Annotated[str, Query(max_length=500)]
) -> Product:
    product = _product(supabase, str(product_id))
    urls: list[str] = list(product.get("image_urls") or [])
    if url not in urls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    result = (
        supabase.table("products")
        .update({"image_urls": [u for u in urls if u != url]})
        .eq("id", str(product_id))
        .execute()
    )
    _forget(supabase, url)
    return _hydrated(supabase, rows(result)[0])


# ------------------------------------------------------------------ orders


def _with_players(supabase: SupabaseDep, order_rows: list[dict[str, Any]]) -> list[OrderAdmin]:
    ids = sorted({str(o["player_id"]) for o in order_rows})
    names: dict[str, dict[str, Any]] = {}
    if ids:
        result = supabase.table("players").select("id, nickname, member_seq").in_("id", ids).execute()
        names = {str(p["id"]): p for p in rows(result)}
    out = []
    for o in order_rows:
        p = names.get(str(o["player_id"]), {})
        seq = p.get("member_seq")
        out.append(
            OrderAdmin.model_validate(
                {
                    **o,
                    "player_nickname": p.get("nickname", "?"),
                    "player_code": f"ND{int(seq):03d}" if seq is not None else "",
                }
            )
        )
    return out


@router.get("/orders", response_model=list[OrderAdmin])
def list_orders(
    supabase: SupabaseDep,
    admin: AdminDep,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> list[OrderAdmin]:
    query = supabase.table("shop_orders").select("*")
    if status_filter:
        query = query.eq("status", status_filter)
    result = query.order("created_at", desc=True).limit(200).execute()
    order_rows = [r for r in rows(result) if not status_filter or r["status"] == status_filter]
    return _with_players(supabase, order_rows)


@router.patch("/orders/{order_id}", response_model=OrderAdmin)
def update_order(order_id: UUID, payload: OrderUpdate, supabase: SupabaseDep, admin: AdminDep) -> OrderAdmin:
    result = supabase.table("shop_orders").select("*").eq("id", str(order_id)).limit(1).execute()
    found = rows(result)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = found[0]
    before, after = order["status"], payload.status
    if after != before and after not in shop_service.ALLOWED_MOVES[before]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="เปลี่ยนสถานะแบบนี้ไม่ได้ — รีเฟรชหน้าแล้วลองใหม่"
        )

    # Stock follows the order: a refused one puts its units back, and one
    # brought back from refused takes them again (if they are still there).
    product_id = order.get("product_id")
    if order["sale_type"] == "stock" and product_id and after != before:
        if after == "rejected":
            shop_service.give_back(supabase, str(product_id), order["size"], int(order["qty"]))
        elif before == "rejected" and not shop_service.take(
            supabase, str(product_id), order["size"], int(order["qty"])
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="ของหมดแล้ว — เอาออเดอร์นี้กลับมาไม่ได้"
            )

    updates: dict[str, Any] = {"status": after, "updated_at": datetime.now(UTC).isoformat()}
    # The note says why a slip was refused; it means nothing on any other state.
    updates["note"] = (payload.note or None) if after == "rejected" else None
    saved = supabase.table("shop_orders").update(updates).eq("id", str(order_id)).execute()
    return _with_players(supabase, rows(saved))[0]


@router.get("/preorder-tally", response_model=list[PreorderTally])
def preorder_tally(supabase: SupabaseDep, admin: AdminDep) -> list[PreorderTally]:
    """What to send to the factory: each pre-order's units per size, from
    orders that have not been refused."""
    products = supabase.table("products").select("*").eq("sale_type", "preorder").execute()
    product_rows = [p for p in rows(products) if p["sale_type"] == "preorder"]
    ordered = shop_service.ordered_by_product(supabase, [str(p["id"]) for p in product_rows])
    out = []
    for p in product_rows:
        mine = ordered.get(str(p["id"]), {})
        by_size = {size: mine.get(size, 0) for size in (p.get("sizes") or [])} or {ONE_SIZE: mine.get(ONE_SIZE, 0)}
        out.append(
            PreorderTally(
                product_id=p["id"],
                name=p["name"],
                preorder_closes_on=p.get("preorder_closes_on"),
                by_size=by_size,
                total=sum(by_size.values()),
            )
        )
    return out
