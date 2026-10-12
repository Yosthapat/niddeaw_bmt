"""Checking every player's stored record against the matches themselves.

A profile shows `players.games/wins/draws/losses` — counters kept up to
date as results come in (migration 0011), not a count of the match rows.
Reading them is one row instead of a scan of the club's whole history,
which is why they exist, but it also means they can drift: the match rows
are the truth, and nothing re-derives the counters from them.

This recomputes each player's record from the completed matches and says
where the two disagree. It judges them with stats_service.build_player_records,
the same function the yearly ranking already computes live, so "a game" here
means exactly what it means everywhere else in the app.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client

from app.db_utils import rows
from app.models.maintenance import PlayerSpell, StatsReport, StatsRow
from app.services import stats_service

PAGE = 1000  # PostgREST's own default ceiling; ask for it explicitly
MATCH_COLUMNS = "team1_player_ids,team2_player_ids,winner,session_id,created_at"


def _all_completed_matches(supabase: Client) -> list[dict[str, Any]]:
    """Every completed match, paged.

    Without the paging this would silently stop at PostgREST's row ceiling
    and report the players above it as having played fewer games than they
    did — an audit that invents drift is worse than no audit.
    """
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = rows(
            supabase.table("matches")
            .select(MATCH_COLUMNS)
            .eq("status", "completed")
            .order("created_at")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def _all_players(supabase: Client) -> list[dict[str, Any]]:
    """Everyone, including members who have been deleted: their profile page
    still reads these counters, and a deleted member's matches still count
    towards whoever played them."""
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = rows(
            supabase.table("players")
            .select("id,nickname,games,wins,draws,losses,is_active")
            .order("nickname")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def audit(supabase: Client, *, apply: bool) -> StatsReport:
    """Compares every player's counters with the matches, and with `apply`
    writes the computed record back.

    The repair is a plain overwrite rather than an adjustment, so running it
    twice is a no-op and it cannot introduce a drift of its own.
    """
    matches = _all_completed_matches(supabase)
    players = _all_players(supabase)
    records = stats_service.build_player_records(matches)  # type: ignore[arg-type]

    results: list[StatsRow] = []
    for player in players:
        pid = UUID(str(player["id"]))
        record = records.get(pid, stats_service.PlayerRecord())
        stored = (
            int(player["games"]),
            int(player["wins"]),
            int(player["draws"]),
            int(player["losses"]),
        )
        real = (record.games, record.wins, record.draws, record.losses)
        if stored == real:
            continue

        if apply:
            supabase.table("players").update(
                {
                    "games": record.games,
                    "wins": record.wins,
                    "draws": record.draws,
                    "losses": record.losses,
                }
            ).eq("id", str(pid)).execute()

        results.append(
            StatsRow(
                player_id=pid,
                nickname=str(player["nickname"]),
                is_active=bool(player["is_active"]),
                stored_games=stored[0],
                real_games=real[0],
                stored_wins=stored[1],
                real_wins=real[1],
                stored_draws=stored[2],
                real_draws=real[2],
                stored_losses=stored[3],
                real_losses=real[3],
            )
        )

    known = {UUID(str(p["id"])) for p in players}
    orphans = sorted(str(pid) for pid in records if pid not in known)

    return StatsReport(
        applied=apply,
        players_checked=len(players),
        matches_counted=len(matches),
        rows=results,
        orphan_player_ids=orphans,
    )


def spells(supabase: Client, player_id: UUID) -> list[PlayerSpell]:
    """How many of a player's games were played on each night.

    The profile's figure is the club's whole history, so "he only played 7"
    and "it says 10" can both be right — three of them were another night.
    This is the breakdown that settles which it is.
    """
    matches = [
        match
        for match in _all_completed_matches(supabase)
        if str(player_id) in match["team1_player_ids"]
        or str(player_id) in match["team2_player_ids"]
    ]
    session_ids = sorted({str(m["session_id"]) for m in matches if m.get("session_id")})
    dates: dict[str, str] = {}
    if session_ids:
        for row in rows(
            supabase.table("sessions").select("id,date").in_("id", session_ids).execute()
        ):
            dates[str(row["id"])] = str(row["date"])

    counts: dict[str, int] = {}
    for match in matches:
        counts[str(match.get("session_id"))] = counts.get(str(match.get("session_id")), 0) + 1

    out = [
        PlayerSpell(
            session_id=sid,
            date=dates.get(sid),
            games=count,
        )
        for sid, count in counts.items()
    ]
    out.sort(key=lambda s: (s.date or "", s.session_id))
    return out
