import base64
import contextlib
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.sponsor import LogoPreview, Sponsor, SponsorOrder, SponsorUpdate, normalise_link
from app.services import logo_service
from app.services.image_service import storage_path_from_url

router = APIRouter(prefix="/api/admin/sponsors", tags=["admin-sponsors"])

LOGO_BUCKET = "sponsors"
MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5MB — same as receipts and the payment QR
# Content-addressed (logo_service.logo_path), so a year is safe.
LOGO_CACHE_SECONDS = "31536000"


def _link(raw: str | None) -> str | None:
    try:
        return normalise_link(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


def _name(raw: str) -> str:
    name = raw.strip()
    if not 1 <= len(name) <= 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ใส่ชื่อผู้สนับสนุน (ไม่เกิน 120 ตัวอักษร)")
    return name


async def _silhouette(file: UploadFile) -> logo_service.Logo:
    contents = await file.read()
    if len(contents) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Logo file too large (max 5MB)",
        )
    try:
        return logo_service.white_silhouette(contents)
    except ValueError as exc:
        detail = (
            "ไม่เห็นโลโก้ในรูปนี้ — ลองไฟล์ที่โลโก้ตัดกับพื้นหลังชัด ๆ"
            if "no logo" in str(exc)
            else "Unsupported image type"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from None


def _store(supabase: SupabaseDep, logo: logo_service.Logo) -> str:
    path = logo_service.logo_path(logo.png)
    bucket = supabase.storage.from_(LOGO_BUCKET)
    bucket.upload(
        path,
        logo.png,
        {"content-type": "image/png", "cache-control": LOGO_CACHE_SECONDS, "upsert": "true"},
    )
    url: str = bucket.get_public_url(path)
    return url


def _forget(supabase: SupabaseDep, logo_url: str | None) -> None:
    """Remove a logo file nothing points at any more. Best effort: a
    failure costs a few KB, never the edit. The five shipped logos live in
    the frontend, not the bucket, and are left alone."""
    if not logo_url:
        return
    stale = storage_path_from_url(logo_url, LOGO_BUCKET)
    if stale:
        with contextlib.suppress(Exception):
            supabase.storage.from_(LOGO_BUCKET).remove([stale])


@router.get("", response_model=list[Sponsor])
def list_sponsors(supabase: SupabaseDep, admin: AdminDep) -> list[Sponsor]:
    result = supabase.table("sponsors").select("*").order("sort_order").order("created_at").execute()
    return [Sponsor.model_validate(row) for row in rows(result)]


@router.post("/logo-preview", response_model=LogoPreview)
async def preview_logo(file: UploadFile, admin: AdminDep) -> LogoPreview:
    """What the band would show for this file, without storing anything —
    so the admin sees the white version before deciding to save."""
    logo = await _silhouette(file)
    encoded = base64.b64encode(logo.png).decode("ascii")
    return LogoPreview(data_uri=f"data:image/png;base64,{encoded}", width=logo.width, height=logo.height)


@router.post("", response_model=Sponsor, status_code=status.HTTP_201_CREATED)
async def create_sponsor(
    supabase: SupabaseDep,
    admin: AdminDep,
    file: UploadFile,
    name: str = Form(...),
    href: str | None = Form(None),
) -> Sponsor:
    clean_name, clean_href = _name(name), _link(href)
    logo = await _silhouette(file)
    last = supabase.table("sponsors").select("sort_order").order("sort_order", desc=True).limit(1).execute()
    last_rows = rows(last)
    next_order = int(last_rows[0]["sort_order"]) + 1 if last_rows else 1
    url = _store(supabase, logo)
    result = (
        supabase.table("sponsors")
        .insert(
            {
                "name": clean_name,
                "href": clean_href,
                "logo_url": url,
                "logo_width": logo.width,
                "logo_height": logo.height,
                "sort_order": next_order,
                "is_visible": True,
            }
        )
        .execute()
    )
    return Sponsor.model_validate(rows(result)[0])


@router.patch("/{sponsor_id}", response_model=Sponsor)
def update_sponsor(
    sponsor_id: UUID, payload: SponsorUpdate, supabase: SupabaseDep, admin: AdminDep
) -> Sponsor:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "href" in updates:
        updates["href"] = _link(updates["href"])
    result = supabase.table("sponsors").update(updates).eq("id", str(sponsor_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sponsor not found")
    return Sponsor.model_validate(result_rows[0])


@router.post("/{sponsor_id}/logo", response_model=Sponsor)
async def replace_logo(
    sponsor_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> Sponsor:
    previous = supabase.table("sponsors").select("logo_url").eq("id", str(sponsor_id)).limit(1).execute()
    previous_rows = rows(previous)
    if not previous_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sponsor not found")
    logo = await _silhouette(file)
    url = _store(supabase, logo)
    result = (
        supabase.table("sponsors")
        .update({"logo_url": url, "logo_width": logo.width, "logo_height": logo.height})
        .eq("id", str(sponsor_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sponsor not found")
    if previous_rows[0].get("logo_url") != url:
        _forget(supabase, previous_rows[0].get("logo_url"))
    return Sponsor.model_validate(result_rows[0])


@router.put("/order", response_model=list[Sponsor])
def reorder_sponsors(payload: SponsorOrder, supabase: SupabaseDep, admin: AdminDep) -> list[Sponsor]:
    """The band runs in this order. One update per sponsor — there are a
    handful, and PostgREST has no batch update by different values."""
    if len(set(payload.ids)) != len(payload.ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ลำดับมีผู้สนับสนุนซ้ำ")
    for position, sponsor_id in enumerate(payload.ids, start=1):
        supabase.table("sponsors").update({"sort_order": position}).eq("id", str(sponsor_id)).execute()
    return list_sponsors(supabase, admin)


@router.delete("/{sponsor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sponsor(sponsor_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    result = supabase.table("sponsors").delete().eq("id", str(sponsor_id)).execute()
    deleted = rows(result)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sponsor not found")
    _forget(supabase, deleted[0].get("logo_url"))
