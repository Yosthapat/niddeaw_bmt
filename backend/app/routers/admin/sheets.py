"""The Google Sheets copy: its setup as the settings page shows it, a sync
an admin starts by hand, and the weekly one a GitHub Action starts.

The weekly endpoint sits outside /api/admin — nobody is logged in at
3 a.m. on a Saturday — and answers only to the shared secret the Action
sends. Unset, it does not exist.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import get_settings
from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.services import sheets_sync
from app.services.google_sheets import ServiceAccount, SheetsApi, SheetsError, spreadsheet_id
from app.services.shop_service import CLUB_TZ

router = APIRouter(prefix="/api/admin/sheets", tags=["admin-sheets"])
internal = APIRouter(prefix="/api/internal", tags=["internal"])

WEEKLY = "อัตโนมัติ (ทุกเช้าวันเสาร์)"


@dataclass(frozen=True)
class SheetsLink:
    api: SheetsApi | None
    has_key: bool
    has_sheet: bool
    account_email: str | None
    problem: str | None


_cached: dict[tuple[str, str], SheetsApi] = {}


def load_sheets() -> SheetsLink:
    """The sheet as configured, or what is missing. Kept between requests,
    so the hour-long Google token is reused rather than fetched each time."""
    settings = get_settings()
    raw_key = (settings.google_service_account_json or "").strip()
    raw_sheet = (settings.sheets_spreadsheet_id or "").strip()
    try:
        account = ServiceAccount.from_json(raw_key) if raw_key else None
        sheet = spreadsheet_id(raw_sheet) if raw_sheet else None
    except SheetsError as e:
        return SheetsLink(None, bool(raw_key), bool(raw_sheet), None, str(e))
    email = account.email if account else None
    if account is None or sheet is None:
        return SheetsLink(None, account is not None, sheet is not None, email, None)
    api = _cached.get((raw_key, sheet))
    if api is None:
        api = _cached[(raw_key, sheet)] = SheetsApi(account, sheet)
    return SheetsLink(api, True, True, email, None)


SheetsDep = Annotated[SheetsLink, Depends(load_sheets)]


class LastSync(BaseModel):
    at: str
    by: str
    rows: int | None
    snapshot: str


class SheetsStatus(BaseModel):
    has_key: bool
    has_sheet: bool
    account_email: str | None
    sheet_url: str | None
    weekly: bool
    problem: str | None
    last: LastSync | None


class SyncDone(BaseModel):
    at: str
    rows: int
    snapshot: str
    removed_snapshots: list[str]
    url: str


def _ready(link: SheetsLink) -> SheetsApi:
    if link.api is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=link.problem or "ยังไม่ได้เชื่อม Google Sheets — ดูขั้นตอนในหน้าตั้งค่า",
        )
    return link.api


def _run(supabase: SupabaseDep, api: SheetsApi, who: str) -> SyncDone:
    try:
        result = sheets_sync.sync(supabase, api, datetime.now(CLUB_TZ), who)
    except SheetsError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return SyncDone(**result.__dict__)


@router.get("", response_model=SheetsStatus)
def sheets_status(link: SheetsDep, admin: AdminDep) -> SheetsStatus:
    last: LastSync | None = None
    problem = link.problem
    if link.api is not None:
        try:
            line = sheets_sync.last_sync(link.api)
        except SheetsError as e:
            # Before the first sync the log tab does not exist yet, and
            # Google calls a range on a missing tab a bad request: that is
            # "never synced", not a problem. A sheet it cannot open is.
            line = None
            if e.kind == "setup":
                problem = str(e)
        if line:
            padded = [*line, "", "", "", ""]
            count = padded[2]
            last = LastSync(
                at=str(padded[0]),
                by=str(padded[1]),
                rows=int(count) if str(count).isdigit() else None,
                snapshot=str(padded[3]),
            )
    return SheetsStatus(
        has_key=link.has_key,
        has_sheet=link.has_sheet,
        account_email=link.account_email,
        sheet_url=link.api.url if link.api else None,
        weekly=bool(get_settings().sheets_sync_secret),
        problem=problem,
        last=last,
    )


@router.post("/sync", response_model=SyncDone)
def sync_now(request: Request, link: SheetsDep, supabase: SupabaseDep, admin: AdminDep) -> SyncDone:
    api = _ready(link)
    who = rows(
        supabase.table("admins").select("username").eq("id", str(admin.admin_id)).limit(1).execute()
    )
    done = _run(supabase, api, who[0]["username"] if who else "แอดมิน")
    request.state.activity_detail = {"rows": done.rows}
    return done


@internal.post("/sheets-sync", response_model=SyncDone)
def weekly_sync(
    link: SheetsDep,
    supabase: SupabaseDep,
    x_sync_secret: Annotated[str | None, Header()] = None,
) -> SyncDone:
    secret = get_settings().sheets_sync_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if x_sync_secret is None or not hmac.compare_digest(x_sync_secret.encode(), secret.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _run(supabase, _ready(link), WEEKLY)
