"""Loads what the quests are worked out from, keeps the result, and writes
the medals down (player_badges) so the LINE page can celebrate new ones and
the home page can list the latest.

The nights, check-ins and matches since counting started are read again at
most every CACHE_SECONDS. When they (or the settings, or anyone's ELO)
differ from what the medals were last worked out from, the medals are
worked out again and player_badges is brought in line: new medals added,
medals the corrected history no longer supports removed. Past months'
monthly medals are never removed: they were earned under that month's
target.
"""

from __future__ import annotations

import dataclasses
import hashlib
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from datetime import time as dtime
from typing import Any, cast

from fastapi import HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.models.quest import (
    BadgeAward,
    BadgeFeedItem,
    MonthState,
    PlayerBadges,
    PodiumState,
    QuestLevel,
    QuestSettings,
    QuestState,
    SecretState,
)
from app.services import quest_service as qs
from app.services import record_service
from app.services.line_checkin import CLUB_TZ

PAGE = 1000
CACHE_SECONDS = 15.0
MATCH_COLUMNS = "id,session_id,team1_player_ids,team2_player_ids,winner,elo_delta_team1,elo_delta_team2,created_at,updated_at,match_no"

# How grand each medal is, for the three shown on a member's card:
# 3 gold, 2 silver, 1 bronze (by level, per quest).
_METAL = {
    "aged": [1, 2, 3, 3],
    "revenge": [2, 3],
    "podium": [1, 1, 1, 2, 2, 2, 3, 3],
    "secret_opener": [1],
    "secret_lights": [2],
    "secret_history": [3],
}


def metal(badge: str, level: int) -> int:
    if badge.startswith("monthly:"):
        return 3
    tiers = _METAL.get(badge, [1, 2, 3])
    return tiers[min(level, len(tiers)) - 1]


@dataclass
class Snapshot:
    key: str
    settings: QuestSettings
    state: dict[str, qs.PlayerQuests]
    names: dict[str, tuple[str, str | None]]  # id -> (nickname, avatar)
    elo: dict[str, int]
    today: date
    held: list[dict[str, Any]]  # player_badges rows after syncing
    # Members who linked LINE, and when (None if no approval is on record).
    # Badges show only for them; everyone's are still counted, so a member
    # who links later finds the medals they already won waiting.
    linked: dict[str, datetime | None] = dataclasses.field(default_factory=dict)


_lock = threading.Lock()
_cached: tuple[float, Snapshot] | None = None


def invalidate() -> None:
    global _cached
    with _lock:
        _cached = None


def _paged(query_factory: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = rows(query_factory().range(offset, offset + PAGE - 1).execute())
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def _dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    d = datetime.fromisoformat(str(v))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _d(v: Any) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def _link_times(supabase: Client) -> dict[str, datetime]:
    """When each LINE account was last approved, by line_user_id: through a
    link request (an existing member) or a sign-up (a new one)."""
    out: dict[str, datetime] = {}
    for table in ("line_link_requests", "line_join_requests"):
        found = _paged(
            lambda table=table: (
                supabase.table(table)
                .select("line_user_id,decided_at")
                .eq("status", "approved")
                .order("decided_at")
            )
        )
        for r in found:
            if r.get("decided_at"):
                at = _dt(r["decided_at"])
                uid = str(r["line_user_id"])
                if uid not in out or at > out[uid]:
                    out[uid] = at
    return out


def load_settings(supabase: Client) -> tuple[QuestSettings, str | None]:
    try:
        found = rows(supabase.table("quest_settings").select("*").eq("id", 1).limit(1).execute())
    except Exception as e:  # the table isn't there until 0038 runs
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ยังไม่ได้เปิดระบบ quest"
        ) from e
    if not found:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ยังไม่ได้เปิดระบบ quest"
        )
    row = found[0]
    return QuestSettings(
        start_date=_d(row["start_date"]), monthly_target=int(row["monthly_target"])
    ), row.get("synced_key")


def _build(supabase: Client) -> Snapshot:
    settings, synced_key = load_settings(supabase)
    start = settings.start_date
    today = datetime.now(CLUB_TZ).date()
    since = datetime.combine(start, dtime.min, CLUB_TZ)

    sessions = _paged(
        lambda: (
            supabase.table("sessions")
            .select("id,date,status")
            .gte("date", start.isoformat())
            .order("date")
        )
    )
    nights = {
        str(s["id"]): qs.Night(id=str(s["id"]), date=_d(s["date"]), closed=s["status"] == "closed")
        for s in sessions
    }
    raw_matches = _paged(
        lambda: (
            supabase.table("matches_numbered")
            .select(MATCH_COLUMNS)
            .eq("status", "completed")
            .gte("created_at", since.isoformat())
            .order("created_at")
        )
    )
    raw_checkins: list[dict[str, Any]] = []
    ids = list(nights)
    for i in range(0, len(ids), 200):
        chunk = ids[i : i + 200]
        raw_checkins += _paged(
            lambda chunk=chunk: (
                supabase.table("checkins")
                .select("session_id,player_id,checkin_time,checkout_time")
                .in_("session_id", chunk)
                .order("checkin_time")
            )
        )
    players = _paged(
        lambda: (
            supabase.table("players")
            .select("id,nickname,avatar_url,elo_score,line_user_id")
            .order("id")
        )
    )
    elo = {str(p["id"]): int(p["elo_score"]) for p in players}
    names = {str(p["id"]): (str(p["nickname"]), p.get("avatar_url")) for p in players}
    times = _link_times(supabase) if any(p.get("line_user_id") for p in players) else {}
    linked = {
        str(p["id"]): times.get(str(p["line_user_id"])) for p in players if p.get("line_user_id")
    }

    h = hashlib.sha1()
    h.update(f"{start}|{settings.monthly_target}|{today.isoformat()[:7]}|".encode())
    for s in sessions:
        h.update(f"s{s['id']}{s['date']}{s['status']}".encode())
    for m in raw_matches:
        h.update(
            f"m{m['id']}{m['winner']}{m.get('elo_delta_team1')}{m.get('elo_delta_team2')}{m.get('updated_at')}".encode()
        )
    for c in raw_checkins:
        h.update(
            f"c{c['session_id']}{c['player_id']}{c['checkin_time']}{c.get('checkout_time')}".encode()
        )
    for pid in sorted(elo):
        h.update(f"p{pid}{elo[pid]}".encode())
    key = h.hexdigest()

    prev = _cached
    if prev and prev[1].key == key:
        # the medals stand; who has linked LINE (and names) may not
        return dataclasses.replace(prev[1], names=names, linked=linked)

    matches = sorted(
        (
            qs.MatchRow(
                id=str(m["id"]),
                session_id=str(m["session_id"]),
                team1=[str(x) for x in m["team1_player_ids"]],
                team2=[str(x) for x in m["team2_player_ids"]],
                winner=str(m["winner"]),
                delta1=int(m.get("elo_delta_team1") or 0),
                delta2=int(m.get("elo_delta_team2") or 0),
                at=_dt(m["created_at"]),
                match_no=int(m["match_no"]) if m.get("match_no") is not None else None,
            )
            for m in raw_matches
            if m.get("winner")
        ),
        key=lambda m: (m.at, m.match_no or 0),
    )
    checkins = [
        qs.CheckinRow(
            session_id=str(c["session_id"]),
            player_id=str(c["player_id"]),
            checkin=_dt(c["checkin_time"]),
            checkout=_dt(c["checkout_time"]) if c.get("checkout_time") else None,
        )
        for c in raw_checkins
    ]
    state = qs.derive(
        players=elo,
        nights=nights,
        matches=matches,
        checkins=checkins,
        all_time=record_service.completed_matches(supabase),  # type: ignore[arg-type]
        monthly_target=settings.monthly_target,
        today=today,
    )
    held = _sync(supabase, state, today, key, synced_key)
    return Snapshot(
        key=key,
        settings=settings,
        state=state,
        names=names,
        elo=elo,
        today=today,
        held=held,
        linked=linked,
    )


def _sync(
    supabase: Client,
    state: dict[str, qs.PlayerQuests],
    today: date,
    key: str,
    synced_key: str | None,
) -> list[dict[str, Any]]:
    existing = _paged(
        lambda: (
            supabase.table("player_badges")
            .select("player_id,badge,level,earned_at,seen_at")
            .order("earned_at")
        )
    )
    if synced_key == key:
        return existing
    want = qs.awards(state)
    have = {(str(r["player_id"]), str(r["badge"]), int(r["level"])): r for r in existing}
    this_month = qs.month_key(today)
    add = [
        {"player_id": p, "badge": b, "level": lv, "earned_at": at.isoformat()}
        for (p, b, lv), at in want.items()
        if (p, b, lv) not in have
    ]
    drop = [
        k
        for k in have
        if k not in want
        and not (k[1].startswith("monthly:") and k[1].split(":", 1)[1] < this_month)
    ]
    for i in range(0, len(add), 200):
        supabase.table("player_badges").insert(cast(Any, add[i : i + 200])).execute()
    for p, b, lv in drop:
        supabase.table("player_badges").delete().eq("player_id", p).eq("badge", b).eq(
            "level", lv
        ).execute()
    supabase.table("quest_settings").update({"synced_key": key}).eq("id", 1).execute()
    kept = [r for k, r in have.items() if k not in set(drop)]
    return kept + [dict(r, seen_at=None) for r in add]


def snapshot_or_none(supabase: Client) -> Snapshot | None:
    """None while quests aren't switched on (0038 not run yet): the pages
    then show no medals, quietly, rather than an error."""
    try:
        return snapshot(supabase)
    except HTTPException as e:
        if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return None
        raise


def snapshot(supabase: Client) -> Snapshot:
    global _cached
    with _lock:
        if _cached and time.monotonic() - _cached[0] < CACHE_SECONDS:
            return _cached[1]
        snap = _build(supabase)
        _cached = (time.monotonic(), snap)
        return snap


# ---- views ---------------------------------------------------------------


def player_badges(snap: Snapshot, player_id: str, *, linked: bool | None = None) -> PlayerBadges:
    """`linked` overrides what the snapshot knows (it can be a few seconds
    behind an approval), for the LINE page, where the member is linked."""
    q = snap.state.get(player_id)
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    quests = []
    for key, prog in q.quests.items():
        other = prog.other
        quests.append(
            QuestState(
                key=key,
                value=prog.value,
                levels=[
                    QuestLevel(threshold=t, earned_at=prog.earned[i])
                    for i, t in enumerate(qs.THRESHOLDS[key])
                ],
                other_id=other,
                other_name=snap.names.get(other, ("", None))[0] if other else None,
            )
        )
    this_month = qs.month_key(snap.today)
    games, got = q.monthly.get(this_month, (0, None))
    past = [
        MonthState(month=mk, target=snap.settings.monthly_target, games=g, earned_at=at)
        for mk, (g, at) in sorted(q.monthly.items(), reverse=True)
        if mk != this_month and at is not None
    ]
    # a past month's medal survives a later correction (see _sync)
    for r in snap.held:
        b = str(r["badge"])
        if str(r["player_id"]) == player_id and b.startswith("monthly:"):
            mk = b.split(":", 1)[1]
            if mk != this_month and all(p.month != mk for p in past):
                past.append(
                    MonthState(
                        month=mk,
                        target=snap.settings.monthly_target,
                        games=0,
                        earned_at=_dt(r["earned_at"]),
                    )
                )
    past.sort(key=lambda m: m.month, reverse=True)
    full = PlayerBadges(
        start_date=snap.settings.start_date,
        quests=quests,
        podium=PodiumState(
            start_rank=q.start_rank, rank=q.rank, elo=snap.elo.get(player_id, 0), earned=q.podium
        ),
        month=MonthState(
            month=this_month, target=snap.settings.monthly_target, games=games, earned_at=got
        ),
        past_months=past,
        secrets=[SecretState(key=k, earned_at=s.earned[0]) for k, s in q.secrets.items()],
    )
    if linked is None:
        linked = player_id in snap.linked
    return full if linked else _locked(snap, player_id, full)


def _locked(snap: Snapshot, player_id: str, full: PlayerBadges) -> PlayerBadges:
    """What a member who hasn't linked LINE shows: every quest still to win,
    and a count of the medals waiting for them once they link."""
    mine = [r for r in snap.held if str(r["player_id"]) == player_id]
    slots = {"monthly" if str(r["badge"]).startswith("monthly:") else str(r["badge"]) for r in mine}
    return PlayerBadges(
        start_date=full.start_date,
        quests=[
            QuestState(
                key=q.key,
                value=0,
                levels=[QuestLevel(threshold=lv.threshold) for lv in q.levels],
            )
            for q in full.quests
        ],
        podium=PodiumState(
            start_rank=full.podium.start_rank,
            rank=full.podium.start_rank,
            elo=full.podium.elo,
            earned=[None] * len(full.podium.earned),
        ),
        month=MonthState(month=full.month.month, target=full.month.target, games=0),
        past_months=[],
        secrets=[SecretState(key=s.key) for s in full.secrets],
        linked=False,
        waiting=len(slots),
        waiting_top=_grandest(mine).get(player_id, []),
    )


def unseen(snap: Snapshot, player_id: str) -> list[BadgeAward]:
    return [
        BadgeAward(badge=str(r["badge"]), level=int(r["level"]), earned_at=_dt(r["earned_at"]))
        for r in snap.held
        if str(r["player_id"]) == player_id and not r.get("seen_at")
    ]


def mark_seen(supabase: Client, player_id: str, items: list[BadgeAward]) -> None:
    now = datetime.now(UTC).isoformat()
    for it in items:
        supabase.table("player_badges").update({"seen_at": now}).eq("player_id", player_id).eq(
            "badge", it.badge
        ).eq("level", it.level).execute()
    invalidate()


def top_badges(snap: Snapshot, per_player: int = 3) -> dict[str, list[BadgeAward]]:
    """Each LINE-linked member's grandest medals, for the member cards."""
    return _grandest([r for r in snap.held if str(r["player_id"]) in snap.linked], per_player)


def _grandest(held: list[dict[str, Any]], per_player: int = 3) -> dict[str, list[BadgeAward]]:
    """Gold before silver before bronze, a quest shown once (its highest
    level), newest first among equals."""
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in held:
        k = (str(r["player_id"]), str(r["badge"]))
        if k not in best or int(r["level"]) > int(best[k]["level"]):
            best[k] = r
    by_player: dict[str, list[dict[str, Any]]] = {}
    for (p, _), r in best.items():
        by_player.setdefault(p, []).append(r)
    out = {}
    for p, rs in by_player.items():
        rs.sort(
            key=lambda r: (metal(str(r["badge"]), int(r["level"])), str(r["earned_at"])),
            reverse=True,
        )
        out[p] = [
            BadgeAward(badge=str(r["badge"]), level=int(r["level"]), earned_at=_dt(r["earned_at"]))
            for r in rs[:per_player]
        ]
    return out


def feed(snap: Snapshot, limit: int = 12) -> list[BadgeFeedItem]:
    """Latest medals in the club worth telling everyone about: silver and
    up, every secret and every monthly medal. Only LINE-linked members',
    and only those won since they linked: the ones that were waiting for
    them are celebrated in LINE, not announced on the home page."""

    def since_linked(r: dict[str, Any]) -> bool:
        pid = str(r["player_id"])
        if pid not in snap.linked:
            return False
        at = snap.linked[pid]
        return at is None or _dt(r["earned_at"]) >= at

    items = [
        r
        for r in snap.held
        if since_linked(r)
        and (
            metal(str(r["badge"]), int(r["level"])) >= 2
            or str(r["badge"]).startswith(("secret_", "monthly:"))
        )
    ]
    items.sort(key=lambda r: str(r["earned_at"]), reverse=True)
    out = []
    for r in items[:limit]:
        name, avatar = snap.names.get(str(r["player_id"]), ("?", None))
        out.append(
            BadgeFeedItem(
                badge=str(r["badge"]),
                level=int(r["level"]),
                earned_at=_dt(r["earned_at"]),
                player_id=str(r["player_id"]),
                nickname=name,
                avatar_url=avatar,
            )
        )
    return out
