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
from app.models.tournament import PublicTournament
from app.services import tournament_service as ts
from app.services import tournament_views as views


@dataclass
class Held:
    """The current tournament's rows, and — made once, the first time a page
    asks — the public view of them and that view as JSON. On the day each
    viewer's poll is then a lookup, not a rebuild: on the free server's
    tenth of a CPU, building the view for 300 phones every 20 s would not
    keep up."""

    row: dict[str, Any]
    snap: views.Snapshot
    _model: PublicTournament | None = None
    _json: bytes | None = None

    def model(self, supabase: Client) -> PublicTournament:
        if self._model is None:
            self._model = views.public_tournament(supabase, self.row, self.snap)
        return self._model

    def json(self, supabase: Client) -> bytes:
        if self._json is None:
            self._json = self.model(supabase).model_dump_json().encode()
        return self._json


@dataclass(frozen=True)
class _Entry:
    at: float
    client: int
    held: Held | None


_lock = threading.Lock()
_entry: _Entry | None = None
_generation = 0


def invalidate() -> None:
    """Forget what is held: the next read goes to the database."""
    global _entry, _generation
    with _lock:
        _entry = None
        _generation += 1


def current(supabase: Client) -> Held | None:
    """The tournament the public pages show, its rows (matches included once
    the schedule is published) and its public view; None when there is none."""
    global _entry
    ttl = get_settings().tournament_cache_seconds
    with _lock:
        cached, generation = _entry, _generation
    if ttl > 0 and cached and cached.client == id(supabase) and time.monotonic() - cached.at < ttl:
        return cached.held
    row = ts.current(supabase)
    held = (
        Held(
            row,
            views.snapshot(
                supabase, str(row["id"]), with_matches=bool(row.get("schedule_published_at"))
            ),
        )
        if row
        else None
    )
    with _lock:
        # A write that landed while this was being read has already dropped
        # the cache; keeping this copy would bring the old rows back.
        if ttl > 0 and generation == _generation:
            _entry = _Entry(time.monotonic(), id(supabase), held)
    return held
