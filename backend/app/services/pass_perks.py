"""What a Niddeaw Pass adds beyond the game (0050_pass_styles.sql).

Looks, which everyone sees:
- a frame round the member's picture (profile, live board, ranking) and a
  face for their profile card. PASS_FRAMES and the foil card show while a
  pass runs;
- LOYAL_FRAMES and the diamond card are earned by holding the pass for
  LOYAL_MONTHS passes in a row, each bought before the last one ran out
  (buying early adds the days on the end: pass_service.buy). A gap starts
  the count again. Once earned they are kept for good, pass or no pass,
  and can't be bought.

And two pages only the holder sees, in LINE, while their pass runs: their
numbers (stats) and a picture of their last night to share (night).
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.services.elo_service import expected_score
from app.services.shop_service import CLUB_TZ

PASS_FRAMES = ("gold", "neon", "crown")
# frame -> passes in a row that earn it
LOYAL_FRAMES = {"moon": 3, "king": 6, "legend": 12}
PASS_CARDS = ("foil",)
LOYAL_CARDS = {"diamond": 12}
MILESTONES = (3, 6, 12)
# Two passes are "in a row" when the second starts by the time the first
# ends. A minute of slack for the clock between reading one and writing
# the next; buying after the pass ran out is a gap.
JOIN_SLACK = timedelta(minutes=1)

# The night's hours, by the club's clock, for the "form" bars.
FORM_BUCKETS = (("early", time(21, 30)), ("mid", time(23, 0)), ("late", time(23, 59, 59)))
MIN_GAMES_TOGETHER = 3


def _when(value: Any) -> datetime:
    text = str(value).replace("Z", "+00:00")
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


# ------------------------------------------------------------ in a row


@dataclass(frozen=True)
class Streak:
    current: int
    """Passes in a row up to now; 0 when no pass runs."""
    best: int
    """The longest run ever: what has been earned."""


def streak(spans: list[tuple[datetime, datetime]], now: datetime) -> Streak:
    best = run = 0
    run_end: datetime | None = None
    for start, end in sorted(spans):
        if run_end is not None and start <= run_end + JOIN_SLACK:
            run += 1
            run_end = max(run_end, end)
        else:
            run, run_end = 1, end
        best = max(best, run)
    # A pass running now is always in the last run: nothing starts after it
    # that isn't joined on.
    current = run if any(s <= now < e for s, e in spans) else 0
    return Streak(current=current, best=best)


def streak_of(passes: list[dict[str, Any]], now: datetime) -> Streak:
    """streak() over one member's pass rows."""
    return streak([(_when(p["starts_at"]), _when(p["ends_at"])) for p in passes], now)


def _spans(all_passes: list[dict[str, Any]]) -> dict[str, list[tuple[datetime, datetime]]]:
    out: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for p in all_passes:
        out[str(p["player_id"])].append((_when(p["starts_at"]), _when(p["ends_at"])))
    return out


def earned(best: int) -> tuple[list[str], list[str]]:
    """The loyal frames and cards a best run of `best` passes has earned."""
    return (
        [f for f, need in LOYAL_FRAMES.items() if best >= need],
        [c for c, need in LOYAL_CARDS.items() if best >= need],
    )


def allowed(running: bool, best: int) -> tuple[list[str], list[str]]:
    frames, cards = earned(best)
    if running:
        frames = [*PASS_FRAMES, *frames]
        cards = [*PASS_CARDS, *cards]
    return frames, cards


# --------------------------------------------------------------- looks


def _style_rows(supabase: Client) -> dict[str, dict[str, Any]]:
    try:
        return {str(r["player_id"]): r for r in rows(supabase.table("pass_styles").select("*").execute())}
    except Exception:  # noqa: BLE001 — before 0050 is run: nobody has a look yet
        return {}


def looks(supabase: Client, now: datetime | None = None) -> dict[str, dict[str, str | None]]:
    """{player_id: {frame, card}} for everyone whose chosen look shows now:
    a pass look while their pass runs, an earned one always."""
    moment = now or datetime.now(UTC)
    styles = _style_rows(supabase)
    if not styles:
        return {}
    spans = _spans(rows(supabase.table("passes").select("player_id,starts_at,ends_at").execute()))
    out: dict[str, dict[str, str | None]] = {}
    for pid, row in styles.items():
        mine = spans.get(pid, [])
        running = any(s <= moment < e for s, e in mine)
        frames, cards = allowed(running, streak(mine, moment).best)
        frame = row.get("frame") if row.get("frame") in frames else None
        card = row.get("card") if row.get("card") in cards else None
        if frame or card:
            out[pid] = {"frame": frame, "card": card}
    return out


def style_of(supabase: Client, player_id: UUID | str) -> dict[str, str | None]:
    row = _style_rows(supabase).get(str(player_id), {})
    return {"frame": row.get("frame"), "card": row.get("card")}


def set_style(supabase: Client, player_id: UUID | str, frame: str | None, card: str | None) -> None:
    pid = str(player_id)
    now = datetime.now(UTC)
    mine = _spans(
        rows(supabase.table("passes").select("player_id,starts_at,ends_at").eq("player_id", pid).execute())
    ).get(pid, [])
    running = any(s <= now < e for s, e in mine)
    frames, cards = allowed(running, streak(mine, now).best)
    if frame is not None and frame not in frames:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="กรอบนี้ยังใช้ไม่ได้")
    if card is not None and card not in cards:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="หน้าการ์ดนี้ยังใช้ไม่ได้")
    supabase.table("pass_styles").upsert(
        {"player_id": pid, "frame": frame, "card": card, "updated_at": now.isoformat()},
        on_conflict="player_id",
    ).execute()


# ------------------------------------------------------- their matches


@dataclass(frozen=True)
class Played:
    at: datetime
    session_id: str
    mates: list[str]
    rivals: list[str]
    result: str
    """"W", "L" or "D"."""
    delta: int
    odds: float | None
    """Their side's chance going in, where the ratings are known."""


def _played(supabase: Client, player_id: str) -> tuple[list[Played], int]:
    """Their finished matches, oldest first, and their rating now."""
    from app.services import elo_history  # one walk over every match, only here

    me = rows(supabase.table("players").select("id,elo_score").eq("id", player_id).limit(1).execute())
    elo_now = int(me[0]["elo_score"]) if me else 0
    before = elo_history.before_ratings(supabase)
    out: list[Played] = []
    for m in rows(supabase.table("matches").select("*").eq("status", "completed").execute()):
        if m.get("status") != "completed":
            continue
        t1 = [str(x) for x in m.get("team1_player_ids") or []]
        t2 = [str(x) for x in m.get("team2_player_ids") or []]
        if player_id not in t1 + t2:
            continue
        side, mine, theirs = ("team1", t1, t2) if player_id in t1 else ("team2", t2, t1)
        winner = m.get("winner")
        result = "D" if winner == "draw" else ("W" if winner == side else "L")
        delta = m.get(f"elo_delta_{side}")
        ratings = before.get(str(m["id"]))
        odds = None
        if ratings is not None:
            ours, other = (ratings[0], ratings[1]) if side == "team1" else (ratings[1], ratings[0])
            odds = expected_score(ours, other)
        out.append(
            Played(
                at=_when(m.get("updated_at") or m["created_at"]),
                session_id=str(m["session_id"]),
                mates=[p for p in mine if p != player_id],
                rivals=theirs,
                result=result,
                delta=int(delta or 0),
                odds=odds,
            )
        )
    out.sort(key=lambda p: p.at)
    return out, elo_now


def _rate(games: list[Played]) -> tuple[int, int]:
    return sum(1 for g in games if g.result == "W"), len(games)


def _best_streak(games: list[Played]) -> int:
    best = run = 0
    for g in games:
        run = run + 1 if g.result == "W" else 0
        best = max(best, run)
    return best


def _bucket(at: datetime) -> str:
    clock = at.astimezone(CLUB_TZ).time()
    # after midnight is still the night: late
    if clock < time(6, 0):
        return "late"
    return next(name for name, until in FORM_BUCKETS if clock < until)


def stats(supabase: Client, player_id: UUID | str) -> dict[str, Any]:
    pid = str(player_id)
    games, elo_now = _played(supabase, pid)
    # ELO after each match, worked back from now
    series: list[dict[str, Any]] = []
    elo = elo_now
    for g in reversed(games):
        series.append({"at": g.at, "elo": elo, "upset": g.result == "W" and g.odds is not None and g.odds < 0.5})
        elo -= g.delta
    series.reverse()

    with_mate: dict[str, list[Played]] = defaultdict(list)
    against: dict[str, list[Played]] = defaultdict(list)
    for g in games:
        for p in g.mates:
            with_mate[p].append(g)
        for p in g.rivals:
            against[p].append(g)

    def pick(groups: dict[str, list[Played]], best: bool) -> dict[str, Any] | None:
        enough = [(p, *_rate(gs)) for p, gs in groups.items() if len(gs) >= MIN_GAMES_TOGETHER]
        if not enough:
            return None
        key = (lambda r: (r[1] / r[2], r[2])) if best else (lambda r: (-r[1] / r[2], r[2]))
        p, wins, total = max(enough, key=key)
        return {"player_id": p, "wins": wins, "games": total}

    form: dict[str, list[int]] = {name: [0, 0] for name, _ in FORM_BUCKETS}
    for g in games:
        b = form[_bucket(g.at)]
        b[0] += g.result == "W"
        b[1] += 1
    return {
        "elo": elo_now,
        "series": series,
        "partner": pick(with_mate, best=True),
        "rival": pick(against, best=False),
        "form": [{"bucket": k, "wins": v[0], "games": v[1]} for k, v in form.items()],
        "last": [g.result for g in games[-10:]],
        "best_streak": _best_streak(games),
        "games": len(games),
    }


def night(supabase: Client, player_id: UUID | str) -> dict[str, Any] | None:
    """Their last night with a result: what it did to their rating, the
    win they least expected, and who they won with most."""
    pid = str(player_id)
    games, elo_now = _played(supabase, pid)
    if not games:
        return None
    last = games[-1].session_id
    tonight = [g for g in games if g.session_id == last]
    after = sum(g.delta for g in games if g.at > tonight[-1].at)
    elo_after = elo_now - after
    gained = sum(g.delta for g in tonight)
    wins = [g for g in tonight if g.result == "W"]
    upset = min((g for g in wins if g.odds is not None and g.odds < 0.5), key=lambda g: g.odds or 1, default=None)
    mates = Counter(p for g in wins for p in g.mates)
    partner = None
    if mates:
        who, won = mates.most_common(1)[0]
        partner = {"player_id": who, "wins": won, "games": sum(1 for g in tonight if who in g.mates)}
    session = rows(supabase.table("sessions").select("id,date").eq("id", last).limit(1).execute())
    return {
        "date": session[0]["date"] if session else tonight[0].at.astimezone(CLUB_TZ).date().isoformat(),
        "games": len(tonight),
        "wins": len(wins),
        "draws": sum(1 for g in tonight if g.result == "D"),
        "elo_before": elo_after - gained,
        "elo_after": elo_after,
        "upset": {"rival_ids": upset.rivals, "odds": round(upset.odds or 0, 2)} if upset else None,
        "partner": partner,
    }
