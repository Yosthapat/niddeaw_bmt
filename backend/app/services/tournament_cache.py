"""The current tournament, kept for a few seconds between reads.

/tournament and the LINE page are the same few rows for everyone, polled
every 20 s by each open page; reading them takes three round trips to
Supabase. So the tournament row and its snapshot (tournament_views.Snapshot)
are kept here for `tournament_cache_seconds`, and every write to the
tournament through this API drops them at once
(middleware/tournament_cache.py), so nobody waits for a change they or the
organisers just made. What changes on its own — an invite or payment
running out — is at most that many seconds late.

One process holds one copy: Render runs a single instance. The snapshot is
shared between requests, so nothing that reads it may change it.
"""

import threading
import time
from dataclasses import dataclass
from typing import Any

from supabase import Client

from app.config import get_settings
from app.services import tournament_service as ts
from app.services import tournament_views as views


@dataclass(frozen=True)
class _Entry:
    at: float
    client: int
    row: dict[str, Any] | None
    snap: views.Snapshot | None


_lock = threading.Lock()
_entry: _Entry | None = None
_generation = 0


def invalidate() -> None:
    """Forget what is held: the next read goes to the database."""
    global _entry, _generation
    with _lock:
        _entry = None
        _generation += 1


def current(supabase: Client) -> tuple[dict[str, Any] | None, views.Snapshot | None]:
    """The tournament the public pages show and its rows (matches included
    once the schedule is published), or (None, None) when there is none."""
    global _entry
    ttl = get_settings().tournament_cache_seconds
    with _lock:
        held, generation = _entry, _generation
    if ttl > 0 and held and held.client == id(supabase) and time.monotonic() - held.at < ttl:
        return held.row, held.snap
    row = ts.current(supabase)
    snap = (
        views.snapshot(
            supabase, str(row["id"]), with_matches=bool(row.get("schedule_published_at"))
        )
        if row
        else None
    )
    with _lock:
        # A write that landed while this was being read has already dropped
        # the cache; keeping this copy would bring the old rows back.
        if ttl > 0 and generation == _generation:
            _entry = _Entry(time.monotonic(), id(supabase), row, snap)
    return row, snap
