from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.services.image_service import thumb_path, thumbnail_jpeg
from app.models.other_income import OtherIncome, OtherIncomeCreate, OtherIncomeUpdate

router = APIRouter(prefix="/api/admin/income", tags=["admin-income"])

# Reuses the `receipts` bucket expenses already upload to (0014_expenses.sql)
# — same "proof of a transaction" photo, no reason for a second bucket.
SLIP_BUCKET = "receipts"

# A thumbnail is named after the receipt it belongs to, so it only
# changes when the receipt does — safe to cache for a year.
THUMBNAIL_CACHE_SECONDS = "31536000"
MAX_SLIP_BYTES = 5 * 1024 * 1024  # 5MB — matches expenses' receipt limit


@router.get("", response_model=list[OtherIncome])
def list_income(supabase: SupabaseDep, admin: AdminDep) -> list[OtherIncome]:
    """Non-billing revenue (sponsor payments, investment injections, etc.),
    most recent first — full history, no month filter, since these are
    expected to be sparse compared to billings."""
    result = supabase.table("other_income").select("*").order("income_date", desc=True).execute()
    return [OtherIncome.model_validate(row) for row in rows(result)]


@router.post("", response_model=OtherIncome, status_code=status.HTTP_201_CREATED)
def create_income(payload: OtherIncomeCreate, supabase: SupabaseDep, admin: AdminDep) -> OtherIncome:
    row = {**payload.model_dump(mode="json"), "created_by": str(admin.admin_id)}
    result = supabase.table("other_income").insert(row).execute()
    return OtherIncome.model_validate(rows(result)[0])


@router.patch("/{income_id}", response_model=OtherIncome)
def update_income(
    income_id: UUID, payload: OtherIncomeUpdate, supabase: SupabaseDep, admin: AdminDep
) -> OtherIncome:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = supabase.table("other_income").update(updates).eq("id", str(income_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")
    return OtherIncome.model_validate(result_rows[0])


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(income_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    result = supabase.table("other_income").delete().eq("id", str(income_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")


@router.post("/{income_id}/slip", response_model=OtherIncome)
async def upload_slip(
    income_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> OtherIncome:
    # Checked up front so a bad id fails before anything reaches storage —
    # otherwise the upload lands and the 404 below orphans it in the bucket.
    existing = supabase.table("other_income").select("id").eq("id", str(income_id)).limit(1).execute()
    if not rows(existing):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")

    contents = await file.read()
    if len(contents) > MAX_SLIP_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Slip file too large (max 5MB)",
        )
    extension = (file.filename or "slip.jpg").rsplit(".", 1)[-1].lower()
    if extension not in {"jpg", "jpeg", "png", "webp", "heic"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type"
        )
    # Timestamped path (not just income_id) so re-uploading a replacement
    # doesn't require a cache-busting query param on the <img> src.
    storage_path = f"{income_id}-{int(datetime.now(timezone.utc).timestamp())}.{extension}"

    supabase.storage.from_(SLIP_BUCKET).upload(
        storage_path,
        contents,
        {"content-type": file.content_type or "image/jpeg", "upsert": "true"},
    )

    # The lists draw this as a 56px square. Without a thumbnail beside it,
    # opening the screen downloads every full-size receipt to paint one.
    # Best-effort: a receipt that cannot be thumbnailed (an exotic format
    # Pillow will not open, say) is still stored and still readable, and
    # the screen falls back to the full image.
    try:
        supabase.storage.from_(SLIP_BUCKET).upload(
            thumb_path(storage_path),
            thumbnail_jpeg(contents),
            {
                "content-type": "image/jpeg",
                "cache-control": THUMBNAIL_CACHE_SECONDS,
                "upsert": "true",
            },
        )
    except Exception:  # noqa: BLE001 - never fail the upload over a thumbnail
        pass

    public_url = supabase.storage.from_(SLIP_BUCKET).get_public_url(storage_path)

    result = (
        supabase.table("other_income")
        .update({"slip_url": public_url})
        .eq("id", str(income_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income entry not found")
    return OtherIncome.model_validate(result_rows[0])
