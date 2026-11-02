"""The admin's backup download, and when the last one was taken.

A POST rather than a GET although it changes nothing: every admin POST goes
into the activity log, and that entry is the "last backed up on … by …"
line the settings page shows — the reminder that makes a monthly backup
actually happen.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.services.backup_service import build_backup
from app.services.shop_service import CLUB_TZ

router = APIRouter(prefix="/api/admin/backup", tags=["admin-backup"])

BACKUP_PATH = "/api/admin/backup"


class LastBackup(BaseModel):
    at: datetime | None = None
    by: str | None = None
    rows: int | None = None


@router.post("")
def download_backup(request: Request, supabase: SupabaseDep, admin: AdminDep) -> Response:
    backup = build_backup(supabase, datetime.now(CLUB_TZ))
    request.state.activity_detail = {"tables": len(backup.counts), "rows": backup.total_rows}
    return Response(
        content=backup.content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{backup.filename}"',
            # Never kept by a proxy or the browser: it is the whole database.
            "Cache-Control": "no-store",
        },
    )


@router.get("/last", response_model=LastBackup)
def last_backup(supabase: SupabaseDep, admin: AdminDep) -> LastBackup:
    found = rows(
        supabase.table("admin_activity_log")
        .select("admin_id, detail, created_at")
        .eq("path", BACKUP_PATH)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not found:
        return LastBackup()
    entry = found[0]
    who = rows(
        supabase.table("admins").select("username").eq("id", entry["admin_id"]).limit(1).execute()
    )
    detail: dict[str, Any] = entry.get("detail") or {}
    total = detail.get("rows")
    return LastBackup(
        at=entry["created_at"],
        by=who[0]["username"] if who else None,
        rows=total if isinstance(total, int) else None,
    )
