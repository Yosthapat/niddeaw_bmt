from datetime import date as DateType
from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.activity_log import AdminActivityLogEntry
from app.models.admin import Admin

router = APIRouter(prefix="/api/admin/activity-log", tags=["admin-activity-log"])

LOG_LIMIT = 200


@router.get("", response_model=list[AdminActivityLogEntry])
def list_activity_log(
    supabase: SupabaseDep,
    admin: AdminDep,
    admin_id: UUID | None = None,
    date: DateType | None = None,
) -> list[AdminActivityLogEntry]:
    """`admin_id` and `date` ("YYYY-MM-DD") both filter, and combine —
    omit either to not filter on it."""
    query = (
        supabase.table("admin_activity_log")
        .select("*")
        .order("created_at", desc=True)
        .limit(LOG_LIMIT)
    )
    if admin_id is not None:
        query = query.eq("admin_id", str(admin_id))
    if date is not None:
        start = datetime.combine(date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        query = query.gte("created_at", start.isoformat()).lt("created_at", end.isoformat())
    logs = rows(query.execute())

    admins_by_id = {
        row["id"]: row["username"]
        for row in rows(supabase.table("admins").select("id, username").execute())
    }

    return [
        AdminActivityLogEntry.model_validate(
            {**entry, "admin_username": admins_by_id.get(entry["admin_id"], "?")}
        )
        for entry in logs
    ]


@router.get("/admins", response_model=list[Admin])
def list_admins_for_filter(supabase: SupabaseDep, admin: AdminDep) -> list[Admin]:
    """The club's admins, for the activity log's admin filter dropdown."""
    result = supabase.table("admins").select("*").order("username").execute()
    return [Admin.model_validate(row) for row in rows(result)]
