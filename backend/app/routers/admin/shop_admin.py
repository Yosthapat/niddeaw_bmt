import contextlib
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.shop import (
    MAX_DETAIL_LABEL,
    MAX_DETAIL_NOTE,
    MAX_DETAILS,
    MAX_IMAGES,
    ONE_SIZE,
    OrderAdmin,
    OrderDelete,
    OrderItemUpdate,
    OrderStatus,
    OrderUpdate,
    PreorderTally,
    Product,
    ProductCreate,
    ProductFields,
    ShopRevenue,
    unit_price,
)
from app.security import verify_password
from app.services import login_throttle, shop_revenue, shop_service
from app.services.image_service import resize_jpeg, storage_path_from_url

router = APIRouter(prefix="/api/admin/shop", tags=["admin-shop"])

SHOP_BUCKET = "shop"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Opened full screen on a phone (the product page's photo viewer), so kept
# large enough to read the print on a shirt at retina density.
IMAGE_MAX_PX = 1600
IMAGE_CACHE_SECONDS = "31536000"  # random object names, so a year is safe
# A turnaround clip: a few seconds, already cut to the web (about 1 MB is
# typical). The cap keeps one careless upload from eating the bucket.
MAX_VIDEO_BYTES = 15 * 1024 * 1024


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _check(merged: dict[str, Any], stock: dict[str, int] | None) -> None:
    """The rules that span fields: a pre-order needs its closing date, stock
    must be given for exactly the sizes the product has, and a size can only
    have its own price if the product has that size."""
    if merged["sale_type"] == "preorder":
        if not merged.get("preorder_closes_on"):
            raise _bad("พรีออเดอร์ต้องมีวันปิดรับ")
        closes, delivers = merged.get("preorder_closes_on"), merged.get("preorder_delivers_on")
        if closes and delivers and str(delivers) < str(closes):
            raise _bad("วันได้ของต้องไม่ก่อนวันปิดรับ")
    if stock is not None and merged["sale_type"] == "stock":
        expected = set(merged["sizes"]) or {ONE_SIZE}
        if set(stock) != expected:
            raise _bad("ใส่จำนวนสต็อกให้ครบทุกไซส์")
    prices = merged.get("size_prices") or {}
    if set(prices) - set(merged["sizes"]):
        raise _bad("ตั้งราคาได้เฉพาะไซส์ที่มีขาย")


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
    fields.setdefault("size_prices", {})
    if payload.sale_type == "stock" and payload.stock is None:
        raise _bad("ใส่จำนวนสต็อกให้ครบทุกไซส์")
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
    if "sizes" in updates and "size_prices" not in updates:
        # A size taken off the list takes its own price with it.
        kept = set(updates["sizes"] or [])
        updates["size_prices"] = {k: v for k, v in (current.get("size_prices") or {}).items() if k in kept}
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
    orders = (
        supabase.table("shop_order_items").select("id, product_id").eq("product_id", str(product_id)).limit(1).execute()
    )
    if [o for o in rows(orders) if str(o.get("product_id")) == str(product_id)]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="สินค้านี้มีออเดอร์แล้ว ลบไม่ได้ — ปิด \"ขายอยู่\" แทน",
        )
    supabase.table("products").delete().eq("id", str(product_id)).execute()
    details = [d.get("url") for d in (product.get("detail_images") or []) if isinstance(d, dict)]
    for url in [*(product.get("image_urls") or []), product.get("video_url"), *details]:
        if url:
            _forget(supabase, url)


def _forget(supabase: SupabaseDep, url: str) -> None:
    """Remove a photo or clip nothing points at any more. Best effort."""
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
    contents = await file.read(MAX_IMAGE_BYTES + 1)  # never more than one byte past the limit
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


def video_kind(head: bytes) -> tuple[str, str] | None:
    """(extension, content type) of an MP4 or WebM file, from its first bytes;
    None for anything else, whatever it is called."""
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "mp4", "video/mp4"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm", "video/webm"
    return None


@router.post("/products/{product_id}/video", response_model=Product)
async def set_video(
    product_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> Product:
    """The clip the product page opens on. A new one replaces the old."""
    old = _product(supabase, str(product_id)).get("video_url")  # before the row changes
    contents = await file.read(MAX_VIDEO_BYTES + 1)
    if len(contents) > MAX_VIDEO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="คลิปใหญ่เกิน 15 MB — ตัดให้สั้นลงหรือลดความละเอียดก่อน",
        )
    kind = video_kind(contents[:16])
    if kind is None:
        raise _bad("ใช้ได้เฉพาะคลิป MP4 หรือ WebM")
    ext, content_type = kind
    path = f"product-video-{uuid.uuid4().hex}.{ext}"
    bucket = supabase.storage.from_(SHOP_BUCKET)
    bucket.upload(path, contents, {"content-type": content_type, "cache-control": IMAGE_CACHE_SECONDS})
    url: str = bucket.get_public_url(path)
    result = supabase.table("products").update({"video_url": url}).eq("id", str(product_id)).execute()
    if old:
        _forget(supabase, old)
    return _hydrated(supabase, rows(result)[0])


@router.delete("/products/{product_id}/video", response_model=Product)
def remove_video(product_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> Product:
    old = _product(supabase, str(product_id)).get("video_url")  # before the row changes
    result = supabase.table("products").update({"video_url": None}).eq("id", str(product_id)).execute()
    if old:
        _forget(supabase, old)
    return _hydrated(supabase, rows(result)[0])


def _details(product: dict[str, Any]) -> list[dict[str, str]]:
    return [d for d in (product.get("detail_images") or []) if isinstance(d, dict) and d.get("url")]


@router.post("/products/{product_id}/details", response_model=Product)
async def add_detail(
    product_id: UUID,
    file: UploadFile,
    supabase: SupabaseDep,
    admin: AdminDep,
    label: Annotated[str, Form(max_length=MAX_DETAIL_LABEL)] = "",
    note: Annotated[str, Form(max_length=MAX_DETAIL_NOTE)] = "",
) -> Product:
    """A close-up for the cinematic page, with its label ("BACK") and a line under it."""
    details = _details(_product(supabase, str(product_id)))  # before the row changes
    if len(details) >= MAX_DETAILS:
        raise _bad(f"ใส่ภาพใกล้ได้สูงสุด {MAX_DETAILS} รูป — ลบรูปเก่าก่อน")
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image file too large (max 5MB)"
        )
    try:
        image = resize_jpeg(contents, IMAGE_MAX_PX)
    except ValueError:
        raise _bad("Unsupported image type") from None
    path = f"product-detail-{uuid.uuid4().hex}.jpg"
    bucket = supabase.storage.from_(SHOP_BUCKET)
    bucket.upload(path, image, {"content-type": "image/jpeg", "cache-control": IMAGE_CACHE_SECONDS})
    entry = {"url": bucket.get_public_url(path), "label": label.strip(), "note": note.strip()}
    result = (
        supabase.table("products").update({"detail_images": [*details, entry]}).eq("id", str(product_id)).execute()
    )
    return _hydrated(supabase, rows(result)[0])


@router.delete("/products/{product_id}/details", response_model=Product)
def remove_detail(
    product_id: UUID, supabase: SupabaseDep, admin: AdminDep, url: Annotated[str, Query(max_length=500)]
) -> Product:
    details = _details(_product(supabase, str(product_id)))
    if not any(d["url"] == url for d in details):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    result = (
        supabase.table("products")
        .update({"detail_images": [d for d in details if d["url"] != url]})
        .eq("id", str(product_id))
        .execute()
    )
    _forget(supabase, url)
    return _hydrated(supabase, rows(result)[0])


# ------------------------------------------------------------------ orders


def _with_players(supabase: SupabaseDep, order_rows: list[dict[str, Any]]) -> list[OrderAdmin]:
    order_rows = shop_service.with_items(supabase, order_rows)
    ids = sorted({str(o["player_id"]) for o in order_rows if o.get("player_id")})
    names: dict[str, dict[str, Any]] = {}
    if ids:
        result = supabase.table("players").select("id, nickname, member_seq").in_("id", ids).execute()
        names = {str(p["id"]): p for p in rows(result)}
    out = []
    for o in order_rows:
        if not o.get("player_id"):
            # A guest's order: the name they typed, and their phone.
            out.append(
                OrderAdmin.model_validate(
                    {**o, "player_nickname": o.get("guest_name") or "?", "player_code": "", "guest": True}
                )
            )
            continue
        p = names.get(str(o["player_id"]), {})
        seq = p.get("member_seq")
        out.append(
            OrderAdmin.model_validate(
                {
                    **o,
                    "player_nickname": p.get("nickname", "?"),
                    "player_code": f"ND{int(seq):03d}" if seq is not None else "",
                    "guest_phone": None,
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

    # Stock follows the order: a refused one puts every line's units back,
    # and one brought back from refused takes them all again — or none, if
    # one of them has gone meanwhile.
    if after != before and "rejected" in (before, after):
        lines = shop_service.items_by_order(supabase, [str(order_id)]).get(str(order_id), [])
        lines = [line for line in lines if str(line.get("order_id")) == str(order_id)]
        if after == "rejected":
            shop_service.give_back_lines(supabase, lines)
        else:
            short = shop_service.take_lines(supabase, lines)
            if short is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"{short['product_name']} {short['size']}".strip()
                    + ": ของหมดแล้ว — เอาออเดอร์นี้กลับมาไม่ได้",
                )

    updates: dict[str, Any] = {"status": after, "updated_at": datetime.now(UTC).isoformat()}
    # The note says why a slip was refused; it means nothing on any other state.
    updates["note"] = (payload.note or None) if after == "rejected" else None
    saved = supabase.table("shop_orders").update(updates).eq("id", str(order_id)).execute()
    return _with_players(supabase, rows(saved))[0]


# A line can be fixed while the order is still in the admin's hands. A
# delivered order has been handed over; a refused one holds no stock, so it
# is reopened first and fixed then.
EDITABLE = {"pending", "confirmed"}


@router.patch("/orders/{order_id}/items/{item_id}", response_model=OrderAdmin)
def update_order_item(
    order_id: UUID, item_id: UUID, payload: OrderItemUpdate, supabase: SupabaseDep, admin: AdminDep
) -> OrderAdmin:
    """Fix one line of an order — a member who picked M meaning XL. The line
    is priced again at the new size's price and the order's total follows,
    so the admin sees what to collect or give back. Stock moves with it: the
    old size goes back on the shelf and the new one is taken."""
    found = rows(supabase.table("shop_orders").select("*").eq("id", str(order_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = found[0]
    if order["status"] not in EDITABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แก้ได้เฉพาะออเดอร์ที่รอตรวจหรือยืนยันแล้ว — ถ้าปฏิเสธไปแล้ว ให้เปิดกลับมาก่อน",
        )
    lines = [
        line
        for line in shop_service.items_by_order(supabase, [str(order_id)]).get(str(order_id), [])
        if str(line.get("order_id")) == str(order_id)
    ]
    line = next((x for x in lines if str(x["id"]) == str(item_id)), None)
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    if not line.get("product_id"):
        raise _bad("สินค้านี้ถูกลบไปแล้ว แก้รายการนี้ไม่ได้")
    product = _product(supabase, str(line["product_id"]))

    sizes: list[str] = list(product.get("sizes") or [])
    size = line["size"] if payload.size is None else payload.size
    qty = int(line["qty"]) if payload.qty is None else payload.qty
    if sizes and size not in sizes:
        raise _bad("สินค้านี้ไม่มีไซส์นี้")
    if not sizes:
        size = ONE_SIZE
    if size == line["size"] and qty == int(line["qty"]):
        raise _bad("No fields to update")
    if size != line["size"] and any(
        str(x.get("product_id")) == str(line["product_id"]) and x["size"] == size for x in lines if x is not line
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ออเดอร์นี้มีไซส์ {size} อยู่แล้ว — แก้จำนวนของบรรทัดนั้นแทน",
        )

    # Stock first, so a size that has run out stops the edit before
    # anything is written. The new units are taken before the old ones go
    # back: if taking fails, nothing has moved.
    if line["sale_type"] == "stock":
        pid = str(line["product_id"])
        if size != line["size"]:
            if not shop_service.take(supabase, pid, size, qty):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"ไซส์ {size} เหลือไม่พอ")
            shop_service.give_back(supabase, pid, line["size"], int(line["qty"]))
        elif qty > int(line["qty"]):
            if not shop_service.take(supabase, pid, size, qty - int(line["qty"])):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"ไซส์ {size} เหลือไม่พอ")
        else:
            shop_service.give_back(supabase, pid, size, int(line["qty"]) - qty)

    price = unit_price(product, size)
    changes = {"size": size, "qty": qty, "unit_price": price, "line_total": round(price * qty, 2)}
    supabase.table("shop_order_items").update(changes).eq("id", str(item_id)).execute()
    total = round(sum(float(changes["line_total"]) if x is line else float(x["line_total"]) for x in lines), 2)
    saved = (
        supabase.table("shop_orders")
        .update({"total": total, "updated_at": datetime.now(UTC).isoformat()})
        .eq("id", str(order_id))
        .execute()
    )
    return _with_players(supabase, rows(saved))[0]


@router.post("/orders/{order_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: UUID, payload: OrderDelete, request: Request, supabase: SupabaseDep, admin: AdminDep
) -> None:
    """Delete an order for good — a test, a duplicate, a mistake.

    Asks for the admin's own password again: a phone left unlocked at the
    court shouldn't be able to wipe orders. Stock the order held goes back
    on the shelf, its slip is removed, and the activity log keeps what was
    deleted (number, buyer, lines, total), since the order itself is gone.
    """
    key = f"delete-order:{admin.admin_id}"
    wait = login_throttle.retry_after_seconds(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="ใส่รหัสผิดหลายครั้ง — รอสักครู่แล้วลองใหม่",
            headers={"Retry-After": str(wait)},
        )
    me = rows(supabase.table("admins").select("id, password_hash").eq("id", str(admin.admin_id)).limit(1).execute())
    if not me or not verify_password(payload.password, me[0]["password_hash"]):
        login_throttle.record_failure(key)
        # 403, not 401: the admin is signed in, the password typed is just
        # wrong — a 401 would sign them out.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="รหัสผ่านไม่ถูกต้อง — ยังไม่ได้ลบอะไร")
    login_throttle.clear(key)

    found = rows(supabase.table("shop_orders").select("*").eq("id", str(order_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = _with_players(supabase, found)[0]

    # A refused order already gave its stock back.
    if order.status != "rejected":
        shop_service.give_back_lines(supabase, [i.model_dump(mode="json") for i in order.items])
    supabase.table("shop_orders").delete().eq("id", str(order_id)).execute()
    _forget(supabase, order.slip_url)

    buyer = f"{order.player_nickname} (คนนอก)" if order.guest else f"{order.player_nickname} {order.player_code}".strip()
    request.state.activity_detail = {
        "order_no": order.order_no,
        "buyer": buyer,
        "items": [" ".join(x for x in (i.product_name, i.size, f"× {i.qty}") if x) for i in order.items],
        "total": order.total,
        "status": order.status,
    }


@router.get("/revenue", response_model=ShopRevenue)
def revenue(supabase: SupabaseDep, admin: AdminDep) -> ShopRevenue:
    """What the shop has taken in (confirmed + delivered orders), what is
    waiting to be checked, and what it made after the shop's costs."""
    return shop_revenue.load(supabase)


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
