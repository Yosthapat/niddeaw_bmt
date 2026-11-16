"""NIDDEAW CUP phase 3 (docs/tournament-spec.md §3–4): the day itself.

A tournament admin calls a match to a free court, enters the result from the
signed score sheet, and the rest follows: the group standings (with the
spec's tie-breaks), the knockout slots filled once a level's groups are done
("A1", "U3" seeds across groups, the 24-team formats), each knockout winner
moved on ("W12"), and every team's shuttle coupons counted.

Scores (spec §3.2–3.3):
- group: two sets to 21, no deuce — the winner of a set has exactly 21, the
  loser 0–20. 2–0 wins (2 points), 1–1 draws (1 each), 0–2 loses.
- knockout: best of three to 21 with deuce, capped at 30.
"""

import random
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import uuid4

from fastapi import status
from supabase import Client

from app.db_utils import rows
from app.services import tournament_draw as td
from app.services import tournament_service as ts

# --- the score rules ---------------------------------------------------------


class BadScore(ValueError):
    """A score the rules don't allow; the message says why, in Thai."""


def _group_set(a: int, b: int, n: int) -> str:
    if max(a, b) != 21 or min(a, b) > 20:
        raise BadScore(f"เซ็ต {n}: รอบกลุ่มไม่มีดิวส์ — ฝั่งที่ชนะต้องได้ 21 พอดี อีกฝั่งไม่เกิน 20")
    return "a" if a > b else "b"


def _ko_set(a: int, b: int, n: int) -> str:
    high, low = max(a, b), min(a, b)
    ok = (
        (high == 21 and low <= 19)
        or (22 <= high <= 29 and low == high - 2)
        or (high == 30 and low in (28, 29))
    )
    if not ok:
        raise BadScore(f"เซ็ต {n}: รอบน็อคเล่นถึง 21 มีดิวส์ ต้องนำ 2 แต้ม ตันที่ 30 — {a}–{b} เป็นไปไม่ได้")
    return "a" if a > b else "b"


def judge(stage: str, sets: list[list[int]]) -> str:
    """'a', 'b' or 'draw' (group only) — or BadScore."""
    for i, s in enumerate(sets, start=1):
        if len(s) != 2 or any(not isinstance(x, int) or x < 0 or x > 30 for x in s):
            raise BadScore(f"เซ็ต {i}: ใส่คะแนนสองฝั่ง 0–30")
    if stage == "group":
        if len(sets) != 2:
            raise BadScore("รอบกลุ่มตี 2 เซ็ตเสมอ")
        won = [_group_set(a, b, i) for i, (a, b) in enumerate(sets, start=1)]
        return won[0] if won[0] == won[1] else "draw"
    if len(sets) not in (2, 3):
        raise BadScore("รอบน็อคตี 2 ใน 3 เซ็ต")
    won = [_ko_set(a, b, i) for i, (a, b) in enumerate(sets, start=1)]
    if len(sets) == 2 and won[0] != won[1]:
        raise BadScore("เสมอกัน 1–1 ต้องตีเซ็ตที่ 3")
    if len(sets) == 3 and won[0] == won[1]:
        raise BadScore("ชนะ 2 เซ็ตแรกแล้ว ไม่มีเซ็ตที่ 3")
    return "a" if won.count("a") >= 2 else "b"


def walkover_sets(winner: str) -> list[list[int]]:
    """A walkover counts 21–0 twice (spec §3.2)."""
    return [[21, 0], [21, 0]] if winner == "a" else [[0, 21], [0, 21]]


# --- standings ---------------------------------------------------------------


@dataclass
class Row:
    team_id: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    points: int = 0
    scored: int = 0
    conceded: int = 0
    rank: int = 0
    group: str = ""
    beat: set[str] = field(default_factory=set)

    @property
    def diff(self) -> int:
        return self.scored - self.conceded

    def per_match(self) -> tuple[float, float, float, float]:
        n = max(1, self.played)
        return (self.points / n, self.diff / n, self.scored / n, -self.conceded / n)


def standings(team_ids: list[str], done: list[dict[str, Any]], group: str = "") -> list[Row]:
    """A group's table: points, then point difference, points for, fewest
    points against, then the match between the two (spec §3.2)."""
    table = {t: Row(team_id=t, group=group) for t in team_ids}
    for m in done:
        a, b = str(m.get("team_a") or ""), str(m.get("team_b") or "")
        if a not in table or b not in table:
            continue
        sa = sum(int(s[0]) for s in m["sets"])
        sb = sum(int(s[1]) for s in m["sets"])
        for me, them, got, lost_pts, side in ((a, b, sa, sb, "a"), (b, a, sb, sa, "b")):
            r = table[me]
            r.played += 1
            r.scored += got
            r.conceded += lost_pts
            if m["winner"] == "draw":
                r.drawn += 1
                r.points += 1
            elif m["winner"] == side:
                r.won += 1
                r.points += 2
                r.beat.add(them)
            else:
                r.lost += 1
    out = sorted(
        table.values(), key=lambda r: (-r.points, -r.diff, -r.scored, r.conceded, r.team_id)
    )
    # head to head between two otherwise level
    for i in range(len(out) - 1):
        x, y = out[i], out[i + 1]
        level = (x.points, x.diff, x.scored, x.conceded) == (y.points, y.diff, y.scored, y.conceded)
        if level and x.team_id in y.beat:
            out[i], out[i + 1] = y, x
    for i, r in enumerate(out, start=1):
        r.rank = i
    return out


def across(rows_: list[Row]) -> list[Row]:
    """Teams from different groups, best first: per match, so a group of
    three is not behind for having played less (spec §3.3). No head to head
    — they never met."""
    return sorted(rows_, key=lambda r: (tuple(-v for v in r.per_match()), r.group, r.team_id))


def is_power_of_two(k: int) -> bool:
    return k >= 2 and k & (k - 1) == 0


@dataclass
class BracketDraw:
    """A bracket whose first round is drawn: its seeds, in the order they
    stand (group winners A B C …), and the teams drawn against them."""

    seeded: list[str]
    pool: list[str]


def seeds(
    level: dict[str, Any], tables: dict[str, list[Row]]
) -> tuple[dict[str, str], dict[str, int], dict[str, BracketDraw]]:
    """For a level whose groups are done: every "A1" group place and every
    "U#"/"L#" seed -> team id; each seed's tier; and, per bracket whose size
    is a power of two, the seeded teams and the pool their opponents are
    drawn from (spec §3.3: the better-placed half seeded, in group order)."""
    slots: dict[str, str] = {}
    for g, table in tables.items():
        for r in table:
            slots[f"{g}{r.rank}"] = r.team_id
    by_rank: dict[int, list[Row]] = {}
    for table in tables.values():
        for r in table:
            by_rank.setdefault(r.rank, []).append(r)
    ranked = {k: across(v) for k, v in by_rank.items()}
    sizes = [len(t) for t in tables.values()]
    n = sum(sizes)
    full = n == int(level["max_teams"]) and all(s == 4 for s in sizes)

    upper: list[tuple[Row, int]] = []
    lower: list[tuple[Row, int]] = []
    if full and n == 24 and not level.get("cut_24"):
        thirds = ranked.get(3, [])
        upper = (
            [(r, 1) for r in ranked[1]] + [(r, 2) for r in ranked[2]] + [(r, 3) for r in thirds[:4]]
        )
        lower = [(r, 3) for r in thirds[4:]] + [(r, 4) for r in ranked.get(4, [])]
    elif full and n == 24:
        seconds = ranked[2]
        upper = [(r, 1) for r in ranked[1]] + [(r, 2) for r in seconds[:2]]
        lower = [(r, 2) for r in seconds[2:]] + [(r, 3) for r in ranked.get(3, [])[:4]]
    else:
        for rank in sorted(ranked):
            (upper if rank <= 2 else lower).extend((r, rank) for r in ranked[rank])
    tiers: dict[str, int] = {}
    draws: dict[str, BracketDraw] = {}
    for bracket, prefix, chosen in (("upper", "U", upper), ("lower", "L", lower)):
        if is_power_of_two(len(chosen)):
            half = len(chosen) // 2
            # the better half are seeds, standing in group order
            top = sorted(chosen[:half], key=lambda x: (x[1], x[0].group))
            chosen = top + chosen[half:]
            draws[bracket] = BracketDraw(
                seeded=[r.team_id for r, _ in top], pool=[r.team_id for r, _ in chosen[half:]]
            )
        for i, (r, tier) in enumerate(chosen, start=1):
            slots[f"{prefix}{i}"] = r.team_id
            tiers[f"{prefix}{i}"] = tier
    return slots, tiers, draws


def draw_opponents(
    seeded: list[str], pool: list[str], group_of: dict[str, str], rng: random.Random | None = None
) -> list[str]:
    """By lot, an opponent from the pool for each seed, never from the seed's
    own group. If no draw can keep every pair apart, the one with fewest
    group-mates meeting."""
    pick = rng or random.SystemRandom()
    best: list[str] = list(pool)
    best_clashes = len(pool) + 1
    for _ in range(500):
        order = list(pool)
        pick.shuffle(order)
        clashes = sum(1 for s, o in zip(seeded, order) if group_of.get(s) == group_of.get(o))
        if clashes < best_clashes:
            best, best_clashes = order, clashes
        if clashes == 0:
            break
    return best


def keep_apart(
    pairs: list[tuple[str, str]],
    slots: dict[str, str],
    tiers: dict[str, int],
    group_of: dict[str, str],
) -> dict[str, str]:
    """First-round pairs where both teams are from one group: swap the second
    seed with another seed of its tier elsewhere, if that leaves both pairs
    clean (spec §3.3). Returns the slots, changed or not."""
    out = dict(slots)

    def clash(a: str, b: str) -> bool:
        ta, tb = out.get(a), out.get(b)
        return bool(ta and tb and group_of.get(ta) == group_of.get(tb))

    def swap(x: str, y: str) -> None:
        out[x], out[y] = out.get(y, ""), out.get(x, "")

    for i, (a, b) in enumerate(pairs):
        if not clash(a, b) or b not in tiers:
            continue
        fixed = False
        for j, (c, d) in enumerate(pairs):
            if i == j:
                continue
            for other in (c, d):
                if other not in tiers or tiers[other] != tiers[b]:
                    continue
                swap(b, other)
                if not clash(a, b) and not clash(c, d):
                    fixed = True
                    break
                swap(b, other)  # no better: put it back
            if fixed:
                break
    return out


# --- reads -------------------------------------------------------------------


def match(supabase: Client, match_id: str) -> dict[str, Any]:
    found = rows(supabase.table(td.MATCHES).select("*").eq("id", match_id).limit(1).execute())
    if not found:
        raise ts.refuse(status.HTTP_404_NOT_FOUND, "ไม่พบแมทนี้")
    return found[0]


def level_tables(
    level_matches: list[dict[str, Any]], level_teams: list[dict[str, Any]]
) -> dict[str, list[Row]]:
    done = [m for m in level_matches if m["stage"] == "group" and m["status"] == "done"]
    tables: dict[str, list[Row]] = {}
    groups: dict[str, list[str]] = {}
    for t in level_teams:
        if t.get("group_label"):
            groups.setdefault(str(t["group_label"]), []).append(str(t["id"]))
    for g, ids in sorted(groups.items()):
        tables[g] = standings(ids, [m for m in done if m.get("group_label") == g], g)
    return tables


def coupons(
    supabase: Client,
    tournament_row: dict[str, Any],
    found_teams: list[dict[str, Any]] | None = None,
    found_matches: list[dict[str, Any]] | None = None,
    found_money: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, int]]:
    """Per team: coupons given (the first set and every set bought), used
    (a coupon a side per shuttle), bought back, and left. Rows the caller
    already holds are used rather than read again."""
    tid = str(tournament_row["id"])
    per_set = int(tournament_row.get("coupons_per_set") or 6)
    out: dict[str, dict[str, int]] = {}
    for t in found_teams if found_teams is not None else ts.teams(supabase, tid):
        if t["status"] in {"confirmed", "slip_review"} or t.get("group_label"):
            out[str(t["id"])] = {"sets": 1, "given": per_set, "used": 0, "returned": 0, "left": 0}
    money = found_money if found_money is not None else money_rows(supabase, tid)
    for m in money:
        team = str(m.get("team_id") or "")
        if team not in out or not m.get("quantity"):
            continue
        if m["category"] == "extra_shuttles":
            out[team]["sets"] += int(m["quantity"])
            out[team]["given"] += int(m["quantity"]) * per_set
        elif m["category"] == "coupon_refund":
            out[team]["returned"] += int(m["quantity"])
    for m in found_matches if found_matches is not None else td.matches(supabase, tid):
        if m["status"] != "done" or m.get("walkover"):
            continue
        for side in ("team_a", "team_b"):
            team = str(m.get(side) or "")
            if team in out:
                out[team]["used"] += int(m.get("shuttles") or 0)
    for c in out.values():
        c["left"] = c["given"] - c["used"] - c["returned"]
    return out


def money_rows(supabase: Client, tournament_id: str) -> list[dict[str, Any]]:
    return rows(supabase.table(ts.MONEY).select("*").eq("tournament_id", tournament_id).execute())


# --- what follows a result ------------------------------------------------------


def _drawn(
    mine: list[dict[str, Any]],
    bracket: str,
    letter: str,
    draw: BracketDraw,
    known: dict[str, str],
    group_of: dict[str, str],
) -> dict[str, str]:
    """The opponents drawn for a bracket's first round ("P#"/"Q#" slots). A
    draw already made stands while it still fits the pool; it is made again
    only if a corrected group result changed who is in it — and never once
    any of that round has been called."""
    first = sorted(
        (
            m
            for m in mine
            if m["stage"] == "ko" and m["bracket"] == bracket and m["slot_b"].startswith(letter)
        ),
        key=lambda m: int(m["slot_b"][1:]),
    )
    current = [str(m.get("team_b") or "") for m in first]
    seeds_now = [known.get(m["slot_a"], "") for m in first]
    if any(m["status"] != "scheduled" for m in first):
        return {m["slot_b"]: t for m, t in zip(first, current) if t}
    fits = sorted(current) == sorted(draw.pool) and all(
        group_of.get(s) != group_of.get(o) for s, o in zip(seeds_now, current)
    )
    chosen = current if fits else draw_opponents(seeds_now, draw.pool, group_of)
    return {m["slot_b"]: t for m, t in zip(first, chosen)}


def refresh(supabase: Client, tournament_id: str, level_id: str) -> None:
    """Fill the knockout of a level from what is known: its seeds and the
    drawn opponents once every group match is done, and each finished
    match's winner — for every match not yet called. A match already on
    court or done keeps its teams."""
    lv = ts.level(supabase, tournament_id, level_id)
    mine = [m for m in td.matches(supabase, tournament_id) if str(m["level_id"]) == level_id]
    teams = [t for t in ts.teams(supabase, tournament_id) if str(t["level_id"]) == level_id]
    groups_done = all(m["status"] == "done" for m in mine if m["stage"] == "group")
    known: dict[str, str] = {}
    if groups_done and any(m["stage"] == "group" for m in mine):
        slots, tiers, draws = seeds(lv, level_tables(mine, teams))
        group_of = {str(t["id"]): str(t.get("group_label") or "") for t in teams}
        for bracket in ("upper", "lower"):
            ko = [m for m in mine if m["stage"] == "ko" and m["bracket"] == bracket]
            if ko:
                widest = max(int(m["round"]) for m in ko)
                pairs = [(m["slot_a"], m["slot_b"]) for m in ko if int(m["round"]) == widest]
                slots = keep_apart(pairs, slots, tiers, group_of)
        known.update(slots)
        for bracket, letter in (("upper", "P"), ("lower", "Q")):
            if bracket in draws:
                known.update(_drawn(mine, bracket, letter, draws[bracket], known, group_of))
    by_no = {int(m["match_no"]): m for m in mine}
    for m in sorted(mine, key=lambda m: int(m["match_no"])):
        if m["stage"] != "ko" or m["status"] != "scheduled":
            continue
        new: dict[str, Any] = {}
        for side, slot in (("team_a", m["slot_a"]), ("team_b", m["slot_b"])):
            if slot.startswith("W"):
                feeder = by_no.get(int(slot[1:]))
                team = None
                if feeder and feeder["status"] == "done" and feeder["winner"] in ("a", "b"):
                    team = feeder["team_a"] if feeder["winner"] == "a" else feeder["team_b"]
            else:
                team = known.get(slot)
            if str(team or "") != str(m.get(side) or ""):
                new[side] = str(team) if team else None
        if new:
            supabase.table(td.MATCHES).update(new).eq("id", str(m["id"])).execute()
            m.update(new)


def _editable(supabase: Client, m: dict[str, Any]) -> None:
    """A result can be corrected until a match it decides has been called."""
    if m["status"] != "done":
        return
    mine = [
        x
        for x in td.matches(supabase, str(m["tournament_id"]))
        if str(x["level_id"]) == str(m["level_id"])
    ]
    if m["stage"] == "group":
        later = [x for x in mine if x["stage"] == "ko" and x["status"] != "scheduled"]
    else:
        later = [
            x
            for x in mine
            if f"W{m['match_no']}" in (x["slot_a"], x["slot_b"]) and x["status"] != "scheduled"
        ]
    if later:
        raise ts.refuse(
            status.HTTP_409_CONFLICT,
            f"แก้ผลไม่ได้แล้ว — แมท #{later[0]['match_no']} ที่ต่อจากผลนี้เรียกลงสนามไปแล้ว",
        )


def _published(supabase: Client, tournament_id: str) -> dict[str, Any]:
    row = ts.tournament(supabase, tournament_id)
    if not row.get("schedule_published_at"):
        raise ts.refuse(status.HTTP_409_CONFLICT, "ประกาศตารางแมทก่อน ถึงจะเริ่มเรียกแมทได้")
    return row


# --- courts ------------------------------------------------------------------


def on_court(supabase: Client, tournament_id: str) -> dict[int, dict[str, Any]]:
    return {
        int(m["court"]): m for m in td.matches(supabase, tournament_id) if m["status"] == "on_court"
    }


def ready(
    supabase: Client,
    tournament_id: str,
    row: dict[str, Any] | None = None,
    found: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Matches that could go on a court now, in their order: both teams
    known, neither on another court, and both rested."""
    row = row or ts.tournament(supabase, tournament_id)
    found = found if found is not None else td.matches(supabase, tournament_id)
    rest = timedelta(minutes=int(row.get("rest_minutes") or 10))
    busy = {
        str(t)
        for m in found
        if m["status"] == "on_court"
        for t in (m.get("team_a"), m.get("team_b"))
        if t
    }
    last: dict[str, Any] = {}
    for m in found:
        if m["status"] == "done" and m.get("finished_at"):
            for t in (m.get("team_a"), m.get("team_b")):
                if t:
                    end = ts.when(m["finished_at"])
                    last[str(t)] = max(last.get(str(t), end), end) if end else last.get(str(t))
    moment = ts.now()
    out = []
    for m in found:
        if m["status"] != "scheduled" or not m.get("team_a") or not m.get("team_b"):
            continue
        sides = [str(m["team_a"]), str(m["team_b"])]
        if any(t in busy for t in sides):
            continue
        if any(t in last and last[t] and last[t] + rest > moment for t in sides):
            continue
        out.append(m)
    return out


def call(supabase: Client, match_id: str, court: int) -> None:
    m = match(supabase, match_id)
    row = _published(supabase, str(m["tournament_id"]))
    if m["status"] != "scheduled":
        raise ts.refuse(status.HTTP_409_CONFLICT, f"แมท #{m['match_no']} เรียกไปแล้ว หรือจบแล้ว")
    if not m.get("team_a") or not m.get("team_b"):
        raise ts.refuse(status.HTTP_409_CONFLICT, f"แมท #{m['match_no']} ยังไม่รู้ว่าทีมไหนแข่ง")
    if row.get("courts") and court > int(row["courts"]):
        raise ts.refuse(status.HTTP_400_BAD_REQUEST, f"งานนี้มี {row['courts']} สนาม")
    if court in on_court(supabase, str(m["tournament_id"])):
        raise ts.refuse(status.HTTP_409_CONFLICT, f"สนาม {court} มีแมทอยู่แล้ว")
    busy = {
        str(t)
        for x in on_court(supabase, str(m["tournament_id"])).values()
        for t in (x.get("team_a"), x.get("team_b"))
        if t
    }
    if str(m["team_a"]) in busy or str(m["team_b"]) in busy:
        raise ts.refuse(status.HTTP_409_CONFLICT, "ทีมในแมทนี้กำลังแข่งอยู่อีกสนาม")
    supabase.table(td.MATCHES).update(
        {"status": "on_court", "court": court, "called_at": ts.iso(ts.now()), "call_count": 1}
    ).eq("id", match_id).execute()


def call_again(supabase: Client, match_id: str) -> None:
    m = match(supabase, match_id)
    if m["status"] != "on_court":
        raise ts.refuse(status.HTTP_409_CONFLICT, "แมทนี้ไม่ได้อยู่ในสนาม")
    supabase.table(td.MATCHES).update(
        {"call_count": int(m.get("call_count") or 0) + 1, "called_at": ts.iso(ts.now())}
    ).eq("id", match_id).execute()


def uncall(supabase: Client, match_id: str) -> None:
    m = match(supabase, match_id)
    if m["status"] != "on_court":
        raise ts.refuse(status.HTTP_409_CONFLICT, "แมทนี้ไม่ได้อยู่ในสนาม")
    supabase.table(td.MATCHES).update(
        {"status": "scheduled", "court": None, "called_at": None, "call_count": 0}
    ).eq("id", match_id).execute()


def record(
    supabase: Client,
    match_id: str,
    sets: list[list[int]] | None,
    shuttles: int,
    admin_id: str,
    walkover_winner: str | None = None,
) -> None:
    """A result from the score sheet, or a walkover; again to correct one."""
    m = match(supabase, match_id)
    _published(supabase, str(m["tournament_id"]))
    if m["status"] == "scheduled" and not walkover_winner:
        raise ts.refuse(status.HTTP_409_CONFLICT, "เรียกแมทนี้ลงสนามก่อน แล้วค่อยกรอกผล")
    if not m.get("team_a") or not m.get("team_b"):
        raise ts.refuse(status.HTTP_409_CONFLICT, "ยังไม่รู้ว่าทีมไหนแข่งแมทนี้")
    _editable(supabase, m)
    if walkover_winner:
        final_sets, winner, used = walkover_sets(walkover_winner), walkover_winner, 0
    else:
        try:
            winner = judge(m["stage"], sets or [])
        except BadScore as exc:
            raise ts.refuse(status.HTTP_400_BAD_REQUEST, str(exc)) from None
        final_sets, used = sets or [], shuttles
    supabase.table(td.MATCHES).update(
        {
            "status": "done",
            "court": None,
            "sets": final_sets,
            "winner": winner,
            "walkover": bool(walkover_winner),
            "shuttles": used,
            "finished_at": m.get("finished_at") or ts.iso(ts.now()),
            "result_by": admin_id,
        }
    ).eq("id", match_id).execute()
    refresh(supabase, str(m["tournament_id"]), str(m["level_id"]))


# --- coupons -----------------------------------------------------------------


def _coupon_money(
    supabase: Client,
    tournament_row: dict[str, Any],
    team_id: str,
    category: str,
    quantity: int,
    unit_price: int,
    paid_via: str,
    receipt_url: str | None,
    admin_id: str,
) -> None:
    supabase.table(ts.MONEY).insert(
        {
            "id": str(uuid4()),
            "tournament_id": str(tournament_row["id"]),
            "direction": "income" if category == "extra_shuttles" else "expense",
            "category": category,
            "category_other": None,
            "amount": quantity * unit_price,
            "entry_date": ts.now().date().isoformat(),
            "paid_by": admin_id if category == "coupon_refund" else None,
            "entrant_id": None,
            "team_id": team_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "paid_via": paid_via,
            "receipt_url": receipt_url,
            "note": None,
            "created_by": admin_id,
            "created_at": ts.iso(ts.now()),
        }
    ).execute()


def sell_sets(
    supabase: Client,
    team_id: str,
    quantity: int,
    paid_via: str,
    receipt_url: str | None,
    admin_id: str,
) -> None:
    t = ts.team(supabase, team_id)
    row = ts.tournament(supabase, str(t["tournament_id"]))
    held = coupons(supabase, row).get(team_id)
    if held is None:
        raise ts.refuse(status.HTTP_409_CONFLICT, "ทีมนี้ไม่ได้อยู่ในการแข่ง")
    if held["returned"]:
        raise ts.refuse(status.HTTP_409_CONFLICT, "ทีมนี้คืนคูปองไปแล้ว ซื้อเพิ่มไม่ได้")
    _coupon_money(
        supabase, row, team_id, "extra_shuttles", quantity, int(row.get("extra_set_price") or 0),
        paid_via, receipt_url, admin_id,
    )  # fmt: skip


def buy_back(
    supabase: Client,
    team_id: str,
    quantity: int,
    paid_via: str,
    receipt_url: str | None,
    admin_id: str,
) -> None:
    t = ts.team(supabase, team_id)
    row = ts.tournament(supabase, str(t["tournament_id"]))
    held = coupons(supabase, row).get(team_id)
    if held is None:
        raise ts.refuse(status.HTTP_409_CONFLICT, "ทีมนี้ไม่ได้อยู่ในการแข่ง")
    if quantity > held["left"]:
        raise ts.refuse(status.HTTP_409_CONFLICT, f"ทีมนี้เหลือคูปองแค่ {held['left']} ใบ")
    _coupon_money(
        supabase, row, team_id, "coupon_refund", quantity, int(row.get("coupon_refund_price") or 0),
        paid_via, receipt_url, admin_id,
    )  # fmt: skip
