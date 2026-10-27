"""Everyone's games, wins, draws and losses, counted from the matches.

Pages used to show players.games/wins/draws/losses: counters bumped as each
result came in (migration 0011). They drifted from the matches they were
meant to summarise. On 27 Oct 2026, 26 of 97 members disagreed with their
own match history (Aekk 10 games against 7 played), mostly from the
double-count closed in #87. The match history, which reads the matches
themselves, was right all along.

Every page that shows a record now asks this module, and this module counts
the completed matches. The members list, a profile, the ranking, a match's
detail and the Hall of Fame therefore agree with the match history by
construction, not by upkeep. The counters are still written, and the ELO
rating still lives on the player, because a rating depends on the order
games were played and cannot be recounted.

The club's whole history is one paged query of three narrow columns, about
a thousand rows a year. The count is kept in memory and thrown away whenever
this process records, corrects or deletes a result. The API runs as a
single process (deploy/render.yaml), so that covers every write the app can
make. CACHE_SECONDS only bounds a change made outside the app, e.g. a row
edited in the Supabase dashboard.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from app.db_utils import rows
from app.services import stats_service

PAGE = 1000  # PostgREST's own default ceiling; ask for it explicitly
CACHE_SECONDS = 60.0
RECORD_COLUMNS = "team1_player_ids,team2_player_ids,winner"

_lock = threading.Lock()
_cached: tuple[float, dict[UUID, stats_service.PlayerRecord]] | None = None


def completed_matches(
    supabase: Client, columns: str = RECORD_COLUMNS, *, since: datetime | None = None
) -> list[dict[str, Any]]:
    """Every completed match (from `since`, if given), paged.

    Without the paging a read stops at PostgREST's row ceiling without a
    word, and everyone past it looks as if they played less than they did.
    The club passed 950 completed matches in October 2026.
    """
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = supabase.table("matches").select(columns).eq("status", "completed")
        if since is not None:
            query = query.gte("created_at", since.isoformat())
        page = rows(query.order("created_at").range(offset, offset + PAGE - 1).execute())
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def all_records(supabase: Client) -> dict[UUID, stats_service.PlayerRecord]:
    """Each player's record over their whole history, by player id.

    A player with no completed match is simply absent; callers treat that
    as an empty record.
    """
    global _cached
    with _lock:
        if _cached is not None and time.monotonic() - _cached[0] < CACHE_SECONDS:
            return _cached[1]
    records = stats_service.build_player_records(completed_matches(supabase))  # type: ignore[arg-type]
    with _lock:
        _cached = (time.monotonic(), records)
    return records


def record_for(supabase: Client, player_id: UUID) -> stats_service.PlayerRecord:
    return all_records(supabase).get(player_id, stats_service.PlayerRecord())


def invalidate() -> None:
    """A result was recorded, corrected or deleted: count again next time."""
    global _cached
    with _lock:
        _cached = None
