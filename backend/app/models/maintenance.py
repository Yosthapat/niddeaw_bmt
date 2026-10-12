"""What a maintenance run reports back."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ThumbnailStatus = Literal["made", "already", "failed"]


class ThumbnailRow(BaseModel):
    """One stored receipt or slip, and what happened to it."""

    label: str
    before_bytes: int
    after_bytes: int
    status: ThumbnailStatus
    detail: str | None = None


class ThumbnailReport(BaseModel):
    """`applied` is false for a dry run, where nothing was written.

    The totals are what the expenses and revenue lists download to paint
    their thumbnails — before, the full-size receipts; after, the
    thumbnails beside them.
    """

    applied: bool
    rows: list[ThumbnailRow]
    before_total: int
    after_total: int
    made: int
    already: int
    failed: int
