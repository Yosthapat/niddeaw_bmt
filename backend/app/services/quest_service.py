"""Quests and badges, worked out from what happened at the club.

Pure: given the nights, check-ins and completed matches since the day
counting started, it says who has earned which medal and when, and how far
each member is towards the next one. No I/O; quest_store.py loads the data,
keeps the result and writes the medals down.

Nothing is stored that the matches don't already say, so a corrected or
deleted result moves the medals with it: the next read works them out
again from the corrected history.

Medals (thresholds per level, bronze → silver → gold → special):
    fire       win streak: wins in a row, a draw or loss starts again
    regular    nights attended (checked in)
    bloodline  weeks in a row with a night; one missed week is let go,
               two in a row start again
    aged       games played
    giant      wins over a team whose average ELO was 100+ higher
    unbeaten   closed nights with 4+ games, all won
    marathon   games in one night
    mixer      different doubles partners
    buddy      wins with the same partner
    revenge    wins over a team with their "เทกันจัง" (most-faced opponent,
               met at least 5 times)
    podium     each ELO tier reached for the first time (above the tier
               they were at when counting started)
    monthly    games in a calendar month ≥ the month's target
    secrets    first to check in (5 nights), last to check out (5 closed
               nights), played in the club's match #1000
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.models.player import EloTier
from app.services.elo_service import get_tier
from app.services.stats_service import CompletedMatchRow, find_nemesis

THRESHOLDS: dict[str, list[int]] = {
    "fire": [3, 5, 10],
    "regular": [5, 20, 50],
    "bloodline": [4, 8, 12],
    "aged": [10, 50, 100, 300],
    "giant": [1, 5, 10],
    "unbeaten": [1, 3, 5],
    "marathon": [6, 7, 8],
    "mixer": [5, 10, 20],
    "buddy": [5, 10, 20],
    "revenge": [1, 3],
}
SECRETS: dict[str, int] = {"secret_opener": 5, "secret_lights": 5, "secret_history": 1}
TIERS: list[EloTier] = ["milk", "beer", "highball", "wine", "soju", "whisky", "vodka", "absinthe"]
GIANT_GAP = 100
UNBEATEN_MIN_GAMES = 4
HISTORY_MATCH_NO = 1000
NEMESIS_MIN_GAMES = 5
"""A เทกันจัง met only once or twice is just the one person you played: beating
them is no payback."""


@dataclass(frozen=True)
class MatchRow:
    id: str
    session_id: str
    team1: list[str]
    team2: list[str]
    winner: str  # team1 | team2 | draw
    delta1: int
    delta2: int
    at: datetime
    match_no: int | None = None


@dataclass(frozen=True)
class Night:
    id: str
    date: date
    closed: bool


@dataclass(frozen=True)
class CheckinRow:
    session_id: str
    player_id: str
    checkin: datetime
    checkout: datetime | None


@dataclass
class _NightRec:
    games: int = 0
    wins: int = 0
    last: datetime | None = None


@dataclass
class Progress:
    """One quest for one member: how far, and when each level was earned."""

    value: int = 0
    earned: list[datetime | None] = field(default_factory=list)
    other: str | None = None  # the partner (buddy) or the เทกันจัง (revenge)


@dataclass
class PlayerQuests:
    quests: dict[str, Progress]
    podium: list[datetime | None]  # index = tier rank (0 milk … 7 absinthe)
    start_rank: int
    rank: int
    monthly: dict[str, tuple[int, datetime | None]]  # "2026-12" -> (games, earned)
    secrets: dict[str, Progress]


def tier_rank(score: int) -> int:
    return TIERS.index(get_tier(score))


def week_index(d: date) -> int:
    """Weeks since year 1, starting on Mondays."""
    return (d.toordinal() - d.weekday()) // 7


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _blank(players: dict[str, int]) -> dict[str, PlayerQuests]:
    out = {}
    for pid, elo in players.items():
        out[pid] = PlayerQuests(
            quests={k: Progress(earned=[None] * len(t)) for k, t in THRESHOLDS.items()},
            podium=[None] * len(TIERS),
            start_rank=tier_rank(elo),
            rank=tier_rank(elo),
            monthly={},
            secrets={k: Progress(earned=[None]) for k in SECRETS},
        )
    return out


def _hit(p: Progress, thresholds: list[int], value: int, at: datetime) -> None:
    for i, t in enumerate(thresholds):
        if p.earned[i] is None and value >= t:
            p.earned[i] = at


def derive(
    *,
    players: dict[str, int],
    nights: dict[str, Night],
    matches: list[MatchRow],
    checkins: list[CheckinRow],
    all_time: list[CompletedMatchRow],
    monthly_target: int,
    today: date,
) -> dict[str, PlayerQuests]:
    """`players`: id -> current ELO. `nights`: the nights since counting
    started. `matches`: completed matches since then, oldest first (used for
    ELO history too). `all_time`: every completed match (team ids and
    winner), for each member's เทกันจัง."""
    out = _blank(players)

    # ELO before each match, walked back from today's rating.
    cur = dict(players)
    before: dict[tuple[str, str], int] = {}
    for m in reversed(matches):
        for team, delta in ((m.team1, m.delta1), (m.team2, m.delta2)):
            for p in team:
                if p not in cur:
                    continue
                cur[p] = cur[p] - delta
                before[(m.id, p)] = cur[p]
    for p, q in out.items():
        q.start_rank = q.rank = tier_rank(cur[p])

    nemesis: dict[str, str] = {}
    for p in players:
        found = find_nemesis_str(p, all_time)
        if found:
            nemesis[p] = found

    streak: dict[str, int] = defaultdict(int)
    partners: dict[str, set[str]] = defaultdict(set)
    partner_wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    night_games: dict[tuple[str, str], _NightRec] = defaultdict(_NightRec)
    month_games: dict[tuple[str, str], int] = defaultdict(int)

    for m in matches:
        night = nights.get(m.session_id)
        if night is None:
            continue
        for team, opp, delta, side in (
            (m.team1, m.team2, m.delta1, "team1"),
            (m.team2, m.team1, m.delta2, "team2"),
        ):
            won = m.winner == side
            mine = [before.get((m.id, p)) for p in team]
            theirs = [before.get((m.id, p)) for p in opp]
            for p in team:
                pq = out.get(p)
                if pq is None:
                    continue
                q = pq
                Q = q.quests
                # aged
                Q["aged"].value += 1
                _hit(Q["aged"], THRESHOLDS["aged"], Q["aged"].value, m.at)
                # fire
                streak[p] = streak[p] + 1 if won else 0
                _hit(Q["fire"], THRESHOLDS["fire"], streak[p], m.at)
                # giant
                a, b = [v for v in mine if v is not None], [v for v in theirs if v is not None]
                if won and len(a) == len(mine) and len(b) == len(theirs) and a and b:
                    gap = sum(b) / len(b) - sum(a) / len(a)
                    if gap >= GIANT_GAP:
                        Q["giant"].value += 1
                        _hit(Q["giant"], THRESHOLDS["giant"], Q["giant"].value, m.at)
                # mixer / buddy
                if len(team) == 2:
                    partner = team[0] if team[1] == p else team[1]
                    partners[p].add(partner)
                    Q["mixer"].value = len(partners[p])
                    _hit(Q["mixer"], THRESHOLDS["mixer"], Q["mixer"].value, m.at)
                    if won:
                        partner_wins[p][partner] += 1
                        n = partner_wins[p][partner]
                        if n > Q["buddy"].value:
                            Q["buddy"].value, Q["buddy"].other = n, partner
                        _hit(Q["buddy"], THRESHOLDS["buddy"], n, m.at)
                # revenge
                nem = nemesis.get(p)
                if nem:
                    Q["revenge"].other = nem
                    if won and nem in opp:
                        Q["revenge"].value += 1
                        _hit(Q["revenge"], THRESHOLDS["revenge"], Q["revenge"].value, m.at)
                # marathon + unbeaten bookkeeping
                rec = night_games[(p, m.session_id)]
                rec.games += 1
                rec.wins += 1 if won else 0
                rec.last = m.at
                Q["marathon"].value = max(Q["marathon"].value, rec.games)
                _hit(Q["marathon"], THRESHOLDS["marathon"], rec.games, m.at)
                # monthly
                mk = month_key(night.date)
                month_games[(p, mk)] += 1
                n_month = month_games[(p, mk)]
                got = q.monthly.get(mk, (0, None))[1]
                if got is None and n_month >= monthly_target:
                    got = m.at
                q.monthly[mk] = (n_month, got)
                # podium
                after = before.get((m.id, p))
                if after is not None:
                    r = tier_rank(after + delta)
                    while r > q.rank:
                        q.rank += 1
                        if q.rank > q.start_rank and q.podium[q.rank] is None:
                            q.podium[q.rank] = m.at
                # match #1000
                if m.match_no == HISTORY_MATCH_NO:
                    s = q.secrets["secret_history"]
                    s.value = 1
                    s.earned[0] = s.earned[0] or m.at

    for p, q in out.items():
        q.quests["fire"].value = streak[p]
        # unbeaten: closed nights only (an open night can still be lost)
        ok = sorted(
            (nights[sid].date, rec.last)
            for (pp, sid), rec in night_games.items()
            if pp == p
            and nights[sid].closed
            and rec.games >= UNBEATEN_MIN_GAMES
            and rec.wins == rec.games
            and rec.last
        )
        u = q.quests["unbeaten"]
        for i, (_, at) in enumerate(ok, start=1):
            u.value = i
            if at is not None:
                _hit(u, THRESHOLDS["unbeaten"], i, at)
        q.rank = tier_rank(players[p])

    # check-ins: nights, weeks in a row, first in / last out
    by_night: dict[str, list[CheckinRow]] = defaultdict(list)
    for c in checkins:
        if c.session_id in nights and c.player_id in out:
            by_night[c.session_id].append(c)
    attended: dict[str, list[tuple[date, datetime]]] = defaultdict(list)
    for sid, rows in by_night.items():
        night = nights[sid]
        for c in rows:
            attended[c.player_id].append((night.date, c.checkin))
    order = sorted(by_night, key=lambda s: (nights[s].date, min(c.checkin for c in by_night[s])))
    for sid in order:
        rows = by_night[sid]
        first = min(rows, key=lambda c: c.checkin)
        s = out[first.player_id].secrets["secret_opener"]
        s.value += 1
        _hit(s, [SECRETS["secret_opener"]], s.value, first.checkin)
        outs = [c for c in rows if c.checkout is not None]
        if nights[sid].closed and outs:
            last = max(outs, key=lambda c: c.checkout or c.checkin)
            s = out[last.player_id].secrets["secret_lights"]
            s.value += 1
            _hit(s, [SECRETS["secret_lights"]], s.value, last.checkout or last.checkin)

    this_week = week_index(today)
    for p, visits in attended.items():
        visits.sort()
        Q = out[p].quests
        Q["regular"].value = 0
        run, last_week = 0, None
        for d, at in visits:
            Q["regular"].value += 1
            _hit(Q["regular"], THRESHOLDS["regular"], Q["regular"].value, at)
            w = week_index(d)
            if last_week is None or w - last_week > 2:
                run = 1
            elif w > last_week:
                run += 1
            last_week = w
            _hit(Q["bloodline"], THRESHOLDS["bloodline"], run, at)
        # still going today? (this week or last may be empty; two empty weeks end it)
        Q["bloodline"].value = run if last_week is not None and this_week - last_week <= 2 else 0
    return out


def find_nemesis_str(player_id: str, all_time: list[CompletedMatchRow]) -> str | None:
    found = find_nemesis(UUID(player_id), all_time)
    return str(found[0]) if found and found[1].encounters >= NEMESIS_MIN_GAMES else None


def awards(state: dict[str, PlayerQuests]) -> dict[tuple[str, str, int], datetime]:
    """Every medal held, as (player, badge, level) -> when it was earned."""
    out: dict[tuple[str, str, int], datetime] = {}
    for p, q in state.items():
        for key, prog in q.quests.items():
            for i, at in enumerate(prog.earned):
                if at is not None:
                    out[(p, key, i + 1)] = at
        for rank, at in enumerate(q.podium):
            if at is not None:
                out[(p, "podium", rank + 1)] = at
        for mk, (_, at) in q.monthly.items():
            if at is not None:
                out[(p, f"monthly:{mk}", 1)] = at
        for key, prog in q.secrets.items():
            if prog.earned[0] is not None:
                out[(p, key, 1)] = prog.earned[0]
    return out
