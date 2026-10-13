"""What a maintenance run reports back."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

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


class StatsRow(BaseModel):
    """One player whose stored record disagrees with their matches.

    Only disagreements are reported: a line here is a player whose profile
    is showing a number the match history does not support.
    """

    player_id: UUID
    nickname: str
    is_active: bool
    stored_games: int
    real_games: int
    stored_wins: int
    real_wins: int
    stored_draws: int
    real_draws: int
    stored_losses: int
    real_losses: int


class StatsReport(BaseModel):
    """`applied` is false for a dry run, where nothing was written.

    `orphan_player_ids` are ids that appear on a completed match but are not
    in the players table at all — a match whose player was hard-deleted.
    Those games are counted for nobody, and no repair here can fix them.
    """

    applied: bool
    players_checked: int
    matches_counted: int
    rows: list[StatsRow]
    orphan_player_ids: list[str]


class PlayerSpell(BaseModel):
    """One night, and how many games a player played in it."""

    session_id: str
    date: str | None
    games: int
