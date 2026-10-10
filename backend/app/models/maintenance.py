"""What a maintenance run reports back."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AvatarShrinkStatus = Literal["shrunk", "already", "failed"]


class AvatarShrinkRow(BaseModel):
    """One member's photo, and what happened to it."""

    player_id: str
    nickname: str
    before_bytes: int
    after_bytes: int
    status: AvatarShrinkStatus
    detail: str | None = None


class AvatarShrinkReport(BaseModel):
    """`applied` is false for a dry run, where nothing was written.

    The totals are what one visitor downloads to see the members list, so
    the screen can say what the run is worth before anyone commits to it.
    """

    applied: bool
    rows: list[AvatarShrinkRow]
    before_total: int
    after_total: int
    shrunk: int
    already: int
    failed: int
