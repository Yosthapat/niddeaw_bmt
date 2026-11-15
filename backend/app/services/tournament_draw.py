"""NIDDEAW CUP phase 2 (docs/tournament-spec.md §3–4): drawing the groups
and laying out the day's matches.

Groups are drawn by lot from a level's confirmed teams: groups of four,
spread as evenly as the count allows (14 teams = 4+4+3+3). The match list
then numbers every match of the day across all levels — group rounds first,
level by level, then the knockout rounds from the widest to the final — and
estimates when each starts from the courts, the minutes per match and the
rest a team gets between matches.

Knockout matches carry slots, not teams: "A1" (group A, 1st), "U3"/"L3"
(the 3rd seed of the upper/lower bracket), "W12" (whoever wins match 12).
Phase 3 fills the teams in as the results come. The pure functions here
take and return plain values so they can be tested without a database.
"""

import heapq
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import status
from supabase import Client

from app.db_utils import rows
from app.services import tournament_service as ts

MATCHES = "tournament_matches"
CLUB_TZ = ZoneInfo("Asia/Bangkok")
GROUP_NAMES = "ABCDEFGH"

# Who plays whom in a group, round by round, by place in the group.
ROUND_ROBIN: dict[int, list[list[tuple[int, int]]]] = {
    4: [[(1, 2), (3, 4)], [(1, 3), (2, 4)], [(1, 4), (2, 3)]],
    3: [[(1, 2)], [(1, 3)], [(2, 3)]],
    2: [[(1, 2)]],
}

# --- the draw ---------------------------------------------------------------


def group_sizes(n: int) -> list[int]:
    """Groups of at most four, as even as possible, the bigger first."""
    if n <= 0:
        return []
    groups = max(1, -(-n // 4))
    base, extra = divmod(n, groups)
    return [base + 1] * extra + [base] * (groups - extra)


def name_key(name: str) -> str:
    return " ".join(name.split()).lower()


def draw(
    teams: list[tuple[str, str]], rng: random.Random | None = None
) -> dict[str, tuple[str, int]]:
    """By lot: team id -> (group letter, place 1–4), for (id, name) pairs.
    Teams of one name — a club's several teams — go to different groups
    whenever there are groups enough; when not, as few share as can."""
    pick = rng or random.SystemRandom()
    sizes = group_sizes(len(teams))
    best: dict[str, tuple[str, int]] = {}
    best_shared = len(teams) + 1
    for _ in range(300):
        order = list(teams)
        pick.shuffle(order)
        # the biggest families first, so they have room to spread
        counts: dict[str, int] = {}
        for _, name in order:
            counts[name_key(name)] = counts.get(name_key(name), 0) + 1
        order.sort(key=lambda t: -counts[name_key(t[1])])
        members: list[list[tuple[str, str]]] = [[] for _ in sizes]
        shared = 0
        for tid, name in order:
            open_groups = [g for g in range(len(sizes)) if len(members[g]) < sizes[g]]
            fresh = [
                g for g in open_groups if all(name_key(n) != name_key(name) for _, n in members[g])
            ]
            g = (
                pick.choice(fresh)
                if fresh
                else min(
                    open_groups,
                    key=lambda x: sum(name_key(n) == name_key(name) for _, n in members[x]),
                )
            )
            shared += 0 if fresh else 1
            members[g].append((tid, name))
        if shared < best_shared:
            best_shared = shared
            best = {}
            for g, group in enumerate(members):
                pick.shuffle(group)
                for pos, (tid, _) in enumerate(group, start=1):
                    best[tid] = (GROUP_NAMES[g], pos)
        if shared == 0:
            break
    return best


# --- the knockout -------------------------------------------------------------


def seed_order(size: int) -> list[int]:
    """Where each seed stands in a bracket of `size` (a power of two), so the
    top seeds meet as late as possible: 8 -> 1 8 4 5 2 7 3 6."""
    order = [1, 2]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order[:size]


def bracket_counts(level: dict[str, Any], n_teams: int, groups: list[int]) -> tuple[int, int]:
    """(upper, lower) — how many teams go to each bracket (spec §3.3)."""
    full = n_teams == int(level["max_teams"]) and all(s == 4 for s in groups)
    if full and n_teams == 24:
        return (8, 8) if level.get("cut_24") else (16, 8)
    upper = sum(min(2, s) for s in groups)
    return upper, n_teams - upper


def first_slots(
    level: dict[str, Any], n_teams: int, groups: list[int], bracket: str
) -> list[str | None]:
    """The first round's places, in bracket order; None is a bye.

    A bracket of 4, 8 or 16 is drawn (spec §3.3): its seeds — the group
    winners (or 3rd places below), in group order A B C … — each against an
    opponent drawn by lot from the other half, never from their own group:
    "A1" v "P1", "B1" v "P2" … ("Q" below). Other sizes seed by record,
    the top seeds taking the byes."""
    full = n_teams == int(level["max_teams"]) and all(s == 4 for s in groups)
    upper, lower = bracket_counts(level, n_teams, groups)
    k = upper if bracket == "upper" else lower
    if k < 2:
        return []
    prefix = "U" if bracket == "upper" else "L"
    if k & (k - 1) == 0:
        half = k // 2
        if full and n_teams in (16, 32):
            place = 1 if bracket == "upper" else 3
            seeded = [f"{GROUP_NAMES[g]}{place}" for g in range(len(groups))]
        else:
            seeded = [f"{prefix}{i}" for i in range(1, half + 1)]
        drawn = "P" if bracket == "upper" else "Q"
        out: list[str | None] = []
        for i, seed in enumerate(seeded, start=1):
            out += [seed, f"{drawn}{i}"]
        return out
    size = 1
    while size < k:
        size *= 2
    return [f"{prefix}{s}" if s <= k else None for s in seed_order(size)]


@dataclass
class Planned:
    level_id: str
    stage: str
    round: int
    slot_a: str
    slot_b: str
    bracket: str | None = None
    group_label: str | None = None
    team_a: str | None = None
    team_b: str | None = None
    # what has to finish first: match keys, or "groups" for the level's group stage
    after: list[str] = field(default_factory=list)
    key: str = ""
    match_no: int = 0
    est_start: datetime | None = None


def knockout(level_id: str, slots: list[str | None], bracket: str) -> list[list[Planned]]:
    """Rounds of a bracket, widest first. A bye's team goes straight on.
    Each later slot names the earlier match it waits for by key ("W:<key>")
    until match numbers are given out."""
    out: list[list[Planned]] = []
    current: list[str | None] = slots
    size = len(slots)
    while size >= 2:
        nxt: list[str | None] = []
        this_round: list[Planned] = []
        for i in range(0, size, 2):
            a, b = current[i], current[i + 1]
            if a is None or b is None:
                nxt.append(a if b is None else b)  # the bye
                continue
            key = f"{level_id}:{bracket}:{size}:{i // 2}"
            this_round.append(
                Planned(
                    level_id=level_id,
                    stage="ko",
                    round=size,
                    bracket=bracket,
                    slot_a=a,
                    slot_b=b,
                    key=key,
                )
            )
            nxt.append(f"W:{key}")
        if this_round:
            out.append(this_round)
        current, size = nxt, size // 2
    return out


# --- the day ----------------------------------------------------------------


def plan(
    levels: list[dict[str, Any]], teams_by_level: dict[str, list[dict[str, Any]]]
) -> list[Planned]:
    """Every match of the day, in playing order, numbered from 1."""
    group_rounds: dict[int, list[Planned]] = {}
    ko_rounds: dict[int, list[Planned]] = {}
    for lv in ts.sorted_levels(levels):
        lid = str(lv["id"])
        placed = [t for t in teams_by_level.get(lid, []) if t.get("group_label")]
        by_group: dict[str, dict[int, dict[str, Any]]] = {}
        for t in placed:
            by_group.setdefault(str(t["group_label"]), {})[int(t["group_pos"])] = t
        sizes = []
        for g in sorted(by_group):
            members = by_group[g]
            size = len(members)
            sizes.append(size)
            for r, pairs in enumerate(ROUND_ROBIN.get(size, []), start=1):
                for a, b in pairs:
                    group_rounds.setdefault(r, []).append(
                        Planned(
                            level_id=lid, stage="group", round=r, group_label=g,
                            slot_a=f"{g}{a}", slot_b=f"{g}{b}",
                            team_a=str(members[a]["id"]), team_b=str(members[b]["id"]),
                            key=f"{lid}:g:{g}:{r}:{a}{b}",
                        )
                    )  # fmt: skip
        if not sizes:
            continue
        for bracket in ("upper", "lower"):
            for rnd in knockout(lid, first_slots(lv, len(placed), sizes, bracket), bracket):
                for m in rnd:
                    m.after = ["groups:" + lid]
                    ko_rounds.setdefault(m.round, []).append(m)

    ordered: list[Planned] = []
    for r in sorted(group_rounds):
        ordered += group_rounds[r]
    for size in sorted(ko_rounds, reverse=True):
        # upper before lower within a round, levels in their order
        ordered += sorted(ko_rounds[size], key=lambda m: 0 if m.bracket == "upper" else 1)
    numbers = {}
    for no, m in enumerate(ordered, start=1):
        m.match_no = no
        numbers[m.key] = no
    for m in ordered:
        deps = [s for s in (m.slot_a, m.slot_b) if s.startswith("W:")]
        m.after += [d[2:] for d in deps]
        m.slot_a = f"W{numbers[m.slot_a[2:]]}" if m.slot_a.startswith("W:") else m.slot_a
        m.slot_b = f"W{numbers[m.slot_b[2:]]}" if m.slot_b.startswith("W:") else m.slot_b
    return ordered


def estimate(
    matches: list[Planned],
    first: datetime,
    courts: int,
    group_minutes: int,
    ko_minutes: int,
    rest_minutes: int,
) -> datetime:
    """Give each match, in order, the earliest free court once its teams have
    rested and what it waits for is done. Returns when the last one ends."""
    free = [first] * max(1, courts)
    heapq.heapify(free)
    team_ready: dict[str, datetime] = {}
    ends: dict[str, datetime] = {}
    groups_end: dict[str, datetime] = {}
    rest = timedelta(minutes=rest_minutes)
    last = first
    for m in matches:
        ready = first
        for t in (m.team_a, m.team_b):
            if t and t in team_ready:
                ready = max(ready, team_ready[t])
        for dep in m.after:
            if dep.startswith("groups:"):
                ready = max(ready, groups_end.get(dep[7:], first) + rest)
            elif dep in ends:
                ready = max(ready, ends[dep] + rest)
        court = heapq.heappop(free)
        start = max(court, ready)
        end = start + timedelta(minutes=group_minutes if m.stage == "group" else ko_minutes)
        heapq.heappush(free, end)
        m.est_start = start
        ends[m.key] = end
        for t in (m.team_a, m.team_b):
            if t:
                team_ready[t] = end + rest
        if m.stage == "group":
            groups_end[m.level_id] = max(groups_end.get(m.level_id, first), end)
        last = max(last, end)
    return last


def day_start(starts_on: Any, at: Any) -> datetime:
    day = starts_on if isinstance(starts_on, date) else date.fromisoformat(str(starts_on))
    clock = at if isinstance(at, time) else time.fromisoformat(str(at or "09:00"))
    return datetime.combine(day, clock, tzinfo=CLUB_TZ)


# --- reads and writes -------------------------------------------------------


def matches(supabase: Client, tournament_id: str) -> list[dict[str, Any]]:
    found = rows(supabase.table(MATCHES).select("*").eq("tournament_id", tournament_id).execute())
    return sorted(found, key=lambda m: int(m["match_no"]))


def has_schedule(supabase: Client, tournament_id: str) -> bool:
    return bool(
        rows(
            supabase.table(MATCHES)
            .select("id")
            .eq("tournament_id", tournament_id)
            .limit(1)
            .execute()
        )
    )


def confirmed(supabase: Client, tournament_id: str, level_id: str) -> list[dict[str, Any]]:
    return [
        t
        for t in ts.teams(supabase, tournament_id)
        if str(t["level_id"]) == level_id and t["status"] == "confirmed"
    ]


def _unlocked(supabase: Client, tournament_id: str) -> None:
    if has_schedule(supabase, tournament_id):
        raise ts.refuse(
            status.HTTP_409_CONFLICT, "ออกตารางแมทไปแล้ว — ล้างตารางก่อน ถึงจะจับฉลากหรือย้ายกลุ่มได้"
        )


def _place(supabase: Client, team_id: str, group: str | None, pos: int | None) -> None:
    supabase.table(ts.TEAMS).update({"group_label": group, "group_pos": pos}).eq(
        "id", team_id
    ).execute()


def draw_level(
    supabase: Client, tournament_id: str, level_id: str, rng: random.Random | None = None
) -> None:
    """Draw this level's groups by lot, again if it was drawn before."""
    _unlocked(supabase, tournament_id)
    ts.level(supabase, tournament_id, level_id)
    pool = confirmed(supabase, tournament_id, level_id)
    if len(pool) < 2:
        raise ts.refuse(status.HTTP_409_CONFLICT, "มือนี้มีทีมยืนยันแล้วไม่ถึง 2 ทีม ยังจับฉลากไม่ได้")
    for t in ts.teams(supabase, tournament_id):
        if str(t["level_id"]) == level_id and t.get("group_label"):
            _place(supabase, str(t["id"]), None, None)
    for team_id, (group, pos) in draw([(str(t["id"]), str(t["name"])) for t in pool], rng).items():
        _place(supabase, team_id, group, pos)


def clear_level(supabase: Client, tournament_id: str, level_id: str) -> None:
    _unlocked(supabase, tournament_id)
    for t in ts.teams(supabase, tournament_id):
        if str(t["level_id"]) == level_id and t.get("group_label"):
            _place(supabase, str(t["id"]), None, None)


def move(supabase: Client, team_id: str, group: str, pos: int) -> None:
    """Put a team in a group's place; whoever held it takes the team's old
    place (a swap), or none if the team had none."""
    t = ts.team(supabase, team_id)
    tid, lid = str(t["tournament_id"]), str(t["level_id"])
    _unlocked(supabase, tid)
    if t["status"] != "confirmed":
        raise ts.refuse(status.HTTP_409_CONFLICT, "จัดกลุ่มได้เฉพาะทีมที่ยืนยันแล้ว")
    holder = next(
        (
            x
            for x in ts.teams(supabase, tid)
            if str(x["level_id"]) == lid
            and x.get("group_label") == group
            and int(x.get("group_pos") or 0) == pos
            and x["status"] not in ts.ENDED
            and str(x["id"]) != team_id
        ),
        None,
    )
    old = (t.get("group_label"), t.get("group_pos"))
    # one at a time, through an empty place: the database allows one team per place
    _place(supabase, team_id, None, None)
    if holder is not None:
        _place(supabase, str(holder["id"]), old[0], old[1])
    _place(supabase, team_id, group, pos)


def build(supabase: Client, tournament_id: str) -> datetime:
    """Number every match of the day and estimate its start. Returns the
    estimated end of the day."""
    row = ts.tournament(supabase, tournament_id)
    if has_schedule(supabase, tournament_id):
        raise ts.refuse(status.HTTP_409_CONFLICT, "มีตารางแมทอยู่แล้ว — ล้างก่อนถ้าจะออกใหม่")
    if not row.get("courts"):
        raise ts.refuse(status.HTTP_400_BAD_REQUEST, "ใส่จำนวนสนามก่อน ระบบใช้ประเมินเวลาแข่ง")
    levels = ts.levels(supabase, tournament_id)
    teams_by_level: dict[str, list[dict[str, Any]]] = {}
    for t in ts.teams(supabase, tournament_id):
        if t["status"] == "confirmed":
            teams_by_level.setdefault(str(t["level_id"]), []).append(t)
    for lv in levels:
        mine = teams_by_level.get(str(lv["id"]), [])
        unplaced = [t for t in mine if not t.get("group_label")]
        if unplaced:
            raise ts.refuse(
                status.HTTP_409_CONFLICT,
                f"มือ {lv['name']} ยังมีทีมที่ไม่มีกลุ่ม ({', '.join(t['name'] for t in unplaced)}) — จับฉลากหรือใส่กลุ่มก่อน",
            )
    planned = plan(levels, teams_by_level)
    if not planned:
        raise ts.refuse(status.HTTP_409_CONFLICT, "ยังไม่มีมือไหนจับฉลากแล้ว")
    end = estimate(
        planned,
        day_start(row["starts_on"], row.get("day_start")),
        int(row["courts"]),
        int(row.get("group_minutes") or 20),
        int(row.get("ko_minutes") or 30),
        int(row.get("rest_minutes") or 10),
    )
    for m in planned:
        supabase.table(MATCHES).insert(
            {
                "id": str(uuid4()),
                "tournament_id": tournament_id,
                "level_id": m.level_id,
                "match_no": m.match_no,
                "stage": m.stage,
                "bracket": m.bracket,
                "round": m.round,
                "group_label": m.group_label,
                "slot_a": m.slot_a,
                "slot_b": m.slot_b,
                "team_a": m.team_a,
                "team_b": m.team_b,
                "est_start": m.est_start.isoformat() if m.est_start else None,
                "status": "scheduled",
                "court": None,
                "called_at": None,
                "call_count": 0,
                "finished_at": None,
                "sets": None,
                "winner": None,
                "walkover": False,
                "shuttles": None,
                "result_by": None,
                "created_at": ts.iso(ts.now()),
            }
        ).execute()
    return end


def clear(supabase: Client, tournament_id: str) -> None:
    row = ts.tournament(supabase, tournament_id)
    if row.get("schedule_published_at"):
        raise ts.refuse(status.HTTP_409_CONFLICT, "ประกาศตารางไปแล้ว — ซ่อนก่อน ถึงจะล้างได้")
    supabase.table(MATCHES).delete().eq("tournament_id", tournament_id).execute()


def publish(supabase: Client, tournament_id: str, on: bool) -> None:
    if on and not has_schedule(supabase, tournament_id):
        raise ts.refuse(status.HTTP_409_CONFLICT, "ยังไม่มีตารางแมทให้ประกาศ")
    supabase.table(ts.TOURNAMENTS).update(
        {"schedule_published_at": ts.iso(ts.now()) if on else None}
    ).eq("id", tournament_id).execute()
