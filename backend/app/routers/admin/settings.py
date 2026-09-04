from fastapi import APIRouter, HTTPException, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.club_settings import ClubSettings, ClubSettingsUpdate

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])

_SINGLETON_ID = 1

QR_BUCKET = "payment-qr"
MAX_QR_BYTES = 5 * 1024 * 1024  # 5MB — matches the receipt upload limit


@router.get("", response_model=ClubSettings)
def get_settings(supabase: SupabaseDep, admin: AdminDep) -> ClubSettings:
    result = (
        supabase.table("club_settings").select("*").eq("id", _SINGLETON_ID).limit(1).execute()
    )
    settings_rows = rows(result)
    if not settings_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club settings not seeded"
        )
    return ClubSettings.model_validate(settings_rows[0])


@router.put("", response_model=ClubSettings)
def update_settings(
    payload: ClubSettingsUpdate, supabase: SupabaseDep, admin: AdminDep
) -> ClubSettings:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = supabase.table("club_settings").update(updates).eq("id", _SINGLETON_ID).execute()
    settings_rows = rows(result)
    if not settings_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club settings not seeded"
        )
    return ClubSettings.model_validate(settings_rows[0])


@router.post("/qr", response_model=ClubSettings)
async def upload_payment_qr(
    file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> ClubSettings:
    """Stores an admin-uploaded payment QR (e.g. a bank's own merchant QR)
    for the "uploaded_qr" payment method — shown as-is, no amount embedded."""
    contents = await file.read()
    if len(contents) > MAX_QR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="QR file too large (max 5MB)",
        )
    extension = (file.filename or "qr.jpg").rsplit(".", 1)[-1].lower()
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type"
        )
    storage_path = f"club-{_SINGLETON_ID}.{extension}"

    supabase.storage.from_(QR_BUCKET).upload(
        storage_path,
        contents,
        {"content-type": file.content_type or "image/jpeg", "upsert": "true"},
    )
    public_url = supabase.storage.from_(QR_BUCKET).get_public_url(storage_path)

    result = (
        supabase.table("club_settings")
        .update({"uploaded_qr_url": public_url})
        .eq("id", _SINGLETON_ID)
        .execute()
    )
    settings_rows = rows(result)
    if not settings_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Club settings not seeded"
        )
    return ClubSettings.model_validate(settings_rows[0])
