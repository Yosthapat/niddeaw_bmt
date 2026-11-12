"""The admin's view of slip QRs (services/slip_check.py): what each slip's
QR said, and reading the slips sent before this existed."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.services import slip_check
from app.services.image_service import storage_path_from_url

router = APIRouter(prefix="/api/admin/slip-checks", tags=["admin-slip-checks"])

MAX_IDS = 200
BACKFILL_BATCH = 12
SOURCES: dict[str, tuple[str, str]] = {
    # kind: (table, storage bucket the slip is in)
    "bill": ("billings", "shop"),
    "topup": ("credit_topups", "shop"),
    "order": ("shop_orders", "shop"),
}


class UsedBefore(BaseModel):
    kind: Literal["bill", "topup", "order"]
    target_id: str
    who: str | None = None
    when: str | None = None
    amount: float | None = None
    gone: bool = False


class SlipCheck(BaseModel):
    target_id: str
    status: Literal["ok", "duplicate", "no_qr", "not_slip", "unchecked"]
    bank: str | None = None
    ref: str | None = None
    used_before: UsedBefore | None = None
    used_count: int = 0


class Backfill(BaseModel):
    done: int
    remaining: int


@router.get("", response_model=list[SlipCheck])
def list_checks(
    supabase: SupabaseDep,
    admin: AdminDep,
    kind: Literal["bill", "topup", "order"],
    ids: Annotated[str, Query(max_length=MAX_IDS * 37)],
) -> list[SlipCheck]:
    wanted = [i.strip() for i in ids.split(",") if i.strip()][:MAX_IDS]
    return [SlipCheck.model_validate(c) for c in slip_check.checks(supabase, kind, wanted)]


def _unread(supabase: SupabaseDep) -> list[tuple[str, dict[str, Any]]]:
    """Every slip on file whose QR hasn't been read for its current image."""
    read = {
        (str(r["kind"]), str(r["target_id"])): str(r.get("slip_url") or "")
        for r in rows(supabase.table(slip_check.TABLE).select("kind,target_id,slip_url").execute())
    }
    out: list[tuple[str, dict[str, Any]]] = []
    for kind, (table, _) in SOURCES.items():
        for r in rows(supabase.table(table).select("id,slip_url").execute()):
            url = r.get("slip_url")
            if url and read.get((kind, str(r["id"]))) != url:
                out.append((kind, r))
    return out


@router.post("/backfill", response_model=Backfill)
def backfill(supabase: SupabaseDep, admin: AdminDep) -> Backfill:
    """Read the next few slips sent before slips were read. Called again
    and again by the admin's screen until nothing is left."""
    todo = _unread(supabase)
    done = 0
    for kind, r in todo[:BACKFILL_BATCH]:
        url = str(r["slip_url"])
        bucket = SOURCES[kind][1]
        path = storage_path_from_url(url, bucket)
        image = b""
        if path:
            try:
                image = supabase.storage.from_(bucket).download(path)
            except Exception:  # noqa: BLE001 — a slip gone from storage reads as "no QR"
                image = b""
        # a slip that can't be fetched is kept as "no QR", so it isn't tried forever
        slip_check.record(supabase, kind, str(r["id"]), url, image)  # type: ignore[arg-type]
        done += 1
    return Backfill(done=done, remaining=len(todo) - done)
