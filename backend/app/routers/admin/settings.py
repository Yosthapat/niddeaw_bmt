from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.club_settings import ClubSettings, ClubSettingsUpdate

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])

_SINGLETON_ID = 1


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
