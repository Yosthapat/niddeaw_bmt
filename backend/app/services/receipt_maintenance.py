"""Making thumbnails for the receipts and slips already in the bucket.

New uploads get one beside them (app/routers/admin/expenses.py and
other_income.py). This is the one-off for everything uploaded before that,
whose list rows currently download the full-size receipt — up to 5MB — to
paint a 56px square.

The receipts themselves are left exactly as they are: the point of
photographing one is reading the small print back off it.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from app.db_utils import rows
from app.models.maintenance import ThumbnailReport, ThumbnailRow
from app.services.image_service import (
    storage_path_from_url,
    thumb_path,
    thumbnail_jpeg,
)

BUCKET = "receipts"
CACHE_SECONDS = "31536000"

# (table, the column holding the image's public URL, a column to name the row by)
SOURCES: list[tuple[str, str, str]] = [
    ("expenses", "receipt_url", "expense_date"),
    ("other_income", "slip_url", "income_date"),
]


def _exists(bucket: Any, path: str) -> bool:
    try:
        bucket.download(path)
        return True
    except Exception:  # noqa: BLE001 - "not found" is the answer, not a fault
        return False


def make_thumbnails(supabase: Client, *, apply: bool) -> ThumbnailReport:
    """Give every stored receipt and slip a thumbnail beside it.

    With `apply` false nothing is written and the report is a forecast.
    Running it again is a no-op: a receipt whose thumbnail is already there
    is skipped without re-encoding it.
    """
    bucket = supabase.storage.from_(BUCKET)
    results: list[ThumbnailRow] = []

    for table, url_column, label_column in SOURCES:
        for row in rows(supabase.table(table).select(f"id,{url_column},{label_column}").execute()):
            url = row.get(url_column)
            if not url:
                continue

            label = f"{table.split('_')[0]} {row.get(label_column, '')}".strip()
            path = storage_path_from_url(str(url), BUCKET)
            if path is None:
                results.append(
                    ThumbnailRow(
                        label=label,
                        before_bytes=0,
                        after_bytes=0,
                        status="failed",
                        detail="image is not in this project's bucket",
                    )
                )
                continue

            target = thumb_path(path)
            if _exists(bucket, target):
                results.append(
                    ThumbnailRow(label=label, before_bytes=0, after_bytes=0, status="already")
                )
                continue

            try:
                original = bucket.download(path)
            except Exception as exc:  # noqa: BLE001 - one missing file, not the batch
                results.append(
                    ThumbnailRow(
                        label=label,
                        before_bytes=0,
                        after_bytes=0,
                        status="failed",
                        detail=f"could not be read: {exc}",
                    )
                )
                continue

            try:
                small = thumbnail_jpeg(original)
            except ValueError as exc:
                results.append(
                    ThumbnailRow(
                        label=label,
                        before_bytes=len(original),
                        after_bytes=0,
                        status="failed",
                        detail=str(exc),
                    )
                )
                continue

            if apply:
                try:
                    bucket.upload(
                        target,
                        small,
                        {
                            "content-type": "image/jpeg",
                            "cache-control": CACHE_SECONDS,
                            "upsert": "true",
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        ThumbnailRow(
                            label=label,
                            before_bytes=len(original),
                            after_bytes=0,
                            status="failed",
                            detail=f"could not be saved: {exc}",
                        )
                    )
                    continue

            results.append(
                ThumbnailRow(
                    label=label,
                    before_bytes=len(original),
                    after_bytes=len(small),
                    status="made",
                )
            )

    return ThumbnailReport(
        applied=apply,
        rows=results,
        before_total=sum(r.before_bytes for r in results),
        after_total=sum(r.after_bytes for r in results),
        made=sum(1 for r in results if r.status == "made"),
        already=sum(1 for r in results if r.status == "already"),
        failed=sum(1 for r in results if r.status == "failed"),
    )
