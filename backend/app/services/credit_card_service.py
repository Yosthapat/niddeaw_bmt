"""Credit cards: the pink or black card a member shows for buying a credit
pack through LINE.

    a pack of 1,000 credit or more   pink card
    a pack of 5,000 credit or more   black card

A card lasts as long as there is credit left. When the balance reaches 0
the card goes, and the next pack bought starts a new one. Within one run
the grandest pack counts: 5,000 then 1,000 is still black. Only packs
bought through LINE (an approved credit_topups row) earn a card; credit an
admin adds at the court keeps a card going but doesn't give one.

Worked out from the ledger, which already says every balance change and
what it was for, so nothing new is stored. The result is kept for
CACHE_SECONDS and dropped whenever a balance changes (credit_service.apply).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Literal

from supabase import Client

from app.db_utils import rows

PINK_AT = 1000
BLACK_AT = 5000
CACHE_SECONDS = 30.0
PAGE = 1000

Tier = Literal["pink", "black"]
_RANK: dict[Tier | None, int] = {None: 0, "pink": 1, "black": 2}


@dataclass(frozen=True)
class Card:
    tier: Tier
    # The ledger row that gave this card: a new one means a new card, which
    # LINE celebrates once.
    since: str


def tier_for(credits: int) -> Tier | None:
    if credits >= BLACK_AT:
        return "black"
    if credits >= PINK_AT:
        return "pink"
    return None


def cards_from(ledger: list[dict[str, Any]], line_topups: set[str]) -> dict[str, Card]:
    """Each member's card now, from their ledger rows (any order) and the
    ids of the top-ups bought through LINE."""
    by_player: dict[str, list[dict[str, Any]]] = {}
    for r in ledger:
        by_player.setdefault(str(r["player_id"]), []).append(r)
    out: dict[str, Card] = {}
    for pid, rs in by_player.items():
        rs.sort(key=lambda r: str(r["created_at"]))
        card: Card | None = None
        for r in rs:
            if int(r["balance_after"]) == 0:
                card = None
                continue
            if r["kind"] != "topup" or str(r.get("ref_id")) not in line_topups:
                continue
            tier = tier_for(int(r["delta"]))
            if tier and _RANK[tier] > _RANK[card.tier if card else None]:
                card = Card(tier=tier, since=str(r["id"]))
        if card and int(rs[-1]["balance_after"]) > 0:
            out[pid] = card
    return out


def _all(supabase: Client, table: str, columns: str, **eq: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = supabase.table(table).select(columns)
        for k, v in eq.items():
            q = q.eq(k, v)
        page = rows(q.order("id").range(offset, offset + PAGE - 1).execute())
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


_lock = threading.Lock()
_cached: tuple[float, dict[str, Card]] | None = None


def invalidate() -> None:
    global _cached
    with _lock:
        _cached = None


def all_cards(supabase: Client) -> dict[str, Card]:
    global _cached
    with _lock:
        if _cached and time.monotonic() - _cached[0] < CACHE_SECONDS:
            return _cached[1]
    ledger = _all(
        supabase, "credit_ledger", "id, player_id, delta, balance_after, kind, ref_id, created_at"
    )
    line_topups = {
        str(t["id"]) for t in _all(supabase, "credit_topups", "id, status", status="approved")
    }
    cards = cards_from(ledger, line_topups)
    with _lock:
        _cached = (time.monotonic(), cards)
    return cards
