"""Quests and badges: what counts towards each medal, and the medals table
kept in line with a corrected history."""

import os
import sys
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.config import get_settings
from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token
from app.services import quest_service as qs
from app.services import quest_store

T0 = datetime(2026, 12, 1, 12, tzinfo=UTC)
TODAY = date(2026, 12, 20)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


class World:
    """A small club: nights, matches and check-ins, fed to derive()."""

    def __init__(self, players: dict[str, int]) -> None:
        self.players = dict(players)  # current ELO
        self.nights: dict[str, qs.Night] = {}
        self.matches: list[qs.MatchRow] = []
        self.checkins: list[qs.CheckinRow] = []
        self.clock = 0

    def night(self, d: date, closed: bool = True) -> str:
        sid = f"n{len(self.nights)}"
        self.nights[sid] = qs.Night(id=sid, date=d, closed=closed)
        return sid

    def match(
        self,
        sid: str,
        t1: list[str],
        t2: list[str],
        winner: str,
        d1: int = 2,
        d2: int = -2,
        no: int | None = None,
    ) -> None:
        self.clock += 15
        self.matches.append(
            qs.MatchRow(
                id=f"m{len(self.matches)}",
                session_id=sid,
                team1=t1,
                team2=t2,
                winner=winner,
                delta1=d1,
                delta2=d2,
                at=at(self.clock),
                match_no=no,
            )
        )

    def checkin(self, sid: str, pid: str, minute: int, out: int | None = None) -> None:
        self.checkins.append(
            qs.CheckinRow(
                session_id=sid,
                player_id=pid,
                checkin=at(minute),
                checkout=at(out) if out is not None else None,
            )
        )

    def derive(
        self, target: int = 20, all_time: list[dict[str, Any]] | None = None
    ) -> dict[str, qs.PlayerQuests]:
        return qs.derive(
            players=self.players,
            nights=self.nights,
            matches=self.matches,
            checkins=self.checkins,
            all_time=all_time or [],
            monthly_target=target,
            today=TODAY,
        )  # type: ignore[arg-type]


def ids(n: int) -> list[str]:
    return [str(uuid4()) for _ in range(n)]


def test_win_streak_starts_again_after_a_draw() -> None:
    a, b, c, d = ids(4)
    w = World({a: 1000, b: 1000, c: 1000, d: 1000})
    n = w.night(date(2026, 12, 2))
    for _ in range(3):
        w.match(n, [a, b], [c, d], "team1")
    w.match(n, [a, b], [c, d], "draw", 0, 0)
    w.match(n, [a, b], [c, d], "team1")
    fire = w.derive()[a].quests["fire"]
    assert fire.earned[0] == w.matches[2].at  # the third win
    assert fire.earned[1] is None
    assert fire.value == 1  # the run going now
    assert w.derive()[c].quests["fire"].earned == [None, None, None]


def test_giant_counts_the_elo_before_the_game() -> None:
    a, b, c, d = ids(4)
    # before the game: a,b 1000; c,d 1200. a,b win +3 / -3.
    w = World({a: 1003, b: 1003, c: 1197, d: 1197})
    n = w.night(date(2026, 12, 2))
    w.match(n, [a, b], [c, d], "team1", 3, -3)
    q = w.derive()
    assert q[a].quests["giant"].value == 1 and q[a].quests["giant"].earned[0] is not None
    assert q[c].quests["giant"].value == 0


def test_a_close_gap_is_not_a_giant() -> None:
    a, b, c, d = ids(4)
    w = World({a: 1050, b: 1050, c: 1100, d: 1100})
    n = w.night(date(2026, 12, 2))
    w.match(n, [a, b], [c, d], "team1", 0, 0)
    assert w.derive()[a].quests["giant"].value == 0


def test_unbeaten_only_on_a_closed_night_with_four_wins() -> None:
    a, b, c, d = ids(4)
    w = World({p: 1000 for p in (a, b, c, d)})
    shut = w.night(date(2026, 12, 2), closed=True)
    still_open = w.night(date(2026, 12, 9), closed=False)
    three = w.night(date(2026, 12, 16), closed=True)
    for _ in range(4):
        w.match(shut, [a, b], [c, d], "team1", 0, 0)
        w.match(still_open, [a, b], [c, d], "team1", 0, 0)
    for _ in range(3):
        w.match(three, [a, b], [c, d], "team1", 0, 0)
    u = w.derive()[a].quests["unbeaten"]
    assert u.value == 1 and u.earned[0] is not None


def test_marathon_mixer_and_buddy() -> None:
    me, *others = ids(8)
    w = World({p: 1000 for p in [me, *others]})
    n = w.night(date(2026, 12, 2))
    partners = others[:5]
    for i in range(10):
        mate = partners[i % 5] if i < 5 else partners[0]
        opp = [p for p in others if p != mate][:2]
        w.match(n, [me, mate], opp, "team1", 0, 0)
    q = w.derive()[me].quests
    # 6 / 7 / 8 games: what a long night at the club's court allows (two
    # games an hour, four hours); ten games earns all three
    assert q["marathon"].value == 10 and all(at is not None for at in q["marathon"].earned)
    assert q["mixer"].value == 5 and q["mixer"].earned[0] is not None
    assert (
        q["buddy"].value == 6
        and q["buddy"].other == partners[0]
        and q["buddy"].earned[0] is not None
    )


def test_revenge_needs_a_win_over_the_most_faced_opponent() -> None:
    a, b, c, d, e, f = ids(6)
    w = World({p: 1000 for p in (a, b, c, d, e, f)})
    n = w.night(date(2026, 12, 2))
    all_time = [
        {"team1_player_ids": [a, b], "team2_player_ids": [c, d], "winner": "team2"}
        for _ in range(4)
    ] + [
        {"team1_player_ids": [a, b], "team2_player_ids": [c, e], "winner": "team2"}
    ]  # c: faced most, 5 times
    w.match(n, [a, b], [e, f], "team1", 0, 0)  # not against c
    assert w.derive(all_time=all_time)[a].quests["revenge"].value == 0
    w.match(n, [a, e], [c, f], "team1", 0, 0)
    r = w.derive(all_time=all_time)[a].quests["revenge"]
    assert r.value == 1 and r.other == c and r.earned[0] is not None


def test_podium_counts_new_tiers_only() -> None:
    a, b, c, d = ids(4)
    # a started at 1495 (Wine) and climbed to 1503 (Soju)
    w = World({a: 1503, b: 1000, c: 1000, d: 1000})
    n = w.night(date(2026, 12, 2))
    w.match(n, [a, b], [c, d], "team1", 4, -4)
    w.match(n, [a, b], [c, d], "team1", 4, -4)
    q = w.derive()[a]
    assert q.start_rank == qs.TIERS.index("wine")
    assert q.podium[qs.TIERS.index("soju")] == w.matches[1].at
    assert q.podium[qs.TIERS.index("wine")] is None  # already there when counting began


def test_monthly_target_and_month_keys() -> None:
    a, b, c, d = ids(4)
    w = World({p: 1000 for p in (a, b, c, d)})
    nov = w.night(date(2026, 11, 28))
    dec = w.night(date(2026, 12, 2))
    for _ in range(3):
        w.match(nov, [a, b], [c, d], "team1", 0, 0)
    for _ in range(2):
        w.match(dec, [a, b], [c, d], "team1", 0, 0)
    m = w.derive(target=3)[a].monthly
    assert m["2026-11"][0] == 3 and m["2026-11"][1] is not None
    assert m["2026-12"] == (2, None)


def test_regular_bloodline_and_the_secrets() -> None:
    a, b = ids(2)
    w = World({a: 1000, b: 1000})
    start = date(2026, 9, 28)  # a Monday
    weeks = [0, 1, 3, 4, 7, 8]  # week 2 missed (let go), weeks 5–6 missed (ends the run)
    for k, wk in enumerate(weeks):
        n = w.night(start + timedelta(weeks=wk))
        w.checkin(n, a, k * 1000, k * 1000 + 300)
        w.checkin(n, b, k * 1000 + 5, k * 1000 + 200)
    q = w.derive()[a]
    assert q.quests["regular"].value == 6 and q.quests["regular"].earned[0] is not None
    assert q.quests["bloodline"].earned[0] is not None  # weeks 0,1,3,4
    assert q.quests["bloodline"].value == 0  # last night is weeks ago
    assert (
        q.secrets["secret_opener"].value == 6 and q.secrets["secret_opener"].earned[0] is not None
    )
    assert q.secrets["secret_lights"].value == 6
    assert w.derive()[b].secrets["secret_opener"].value == 0


def test_no_payback_on_someone_met_once() -> None:
    a, b, c, d = ids(4)
    w = World({p: 1000 for p in (a, b, c, d)})
    n = w.night(date(2026, 12, 2))
    w.match(n, [a, b], [c, d], "team1", 0, 0)
    once = [{"team1_player_ids": [a, b], "team2_player_ids": [c, d], "winner": "team1"}]
    r = w.derive(all_time=once)[a].quests["revenge"]
    assert r.value == 0 and r.other is None


def test_match_one_thousand() -> None:
    a, b, c, d = ids(4)
    w = World({p: 1000 for p in (a, b, c, d)})
    n = w.night(date(2026, 12, 2))
    w.match(n, [a, b], [c, d], "team2", 0, 0, no=1000)
    assert w.derive()[c].secrets["secret_history"].earned[0] is not None
    assert w.derive()[a].secrets["secret_history"].earned[0] is not None


# ---- the API, against the in-memory database --------------------------------

BALL_LINE = "U" + "a" * 32


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def member() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(BALL_LINE, 'Ball LINE')}"}


def player(nickname: str, seq: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "nickname": nickname,
        "member_seq": seq,
        "elo_score": 1000,
        "elo_level": "beer",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        **extra,
    }


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[MiniSupabase]:
    s = get_settings()
    monkeypatch.setattr(s, "line_login_channel_id", "1234567890")
    monkeypatch.setattr(s, "line_liff_id", "1234567890-AbCdEfGh")
    ball, bank, bam, bow = (
        player("Ball", 1, line_user_id=BALL_LINE),
        player("Bank", 2),
        player("Bam", 3),
        player("Bow", 4),
    )
    night = {
        "id": str(uuid4()),
        "date": "2026-12-02",
        "location": "court",
        "rate_per_hour": 0,
        "status": "closed",
        "created_by": str(uuid4()),
        "created_at": "2026-12-02T11:00:00Z",
    }
    old = dict(night, id=str(uuid4()), date="2026-10-01", created_at="2026-10-01T11:00:00Z")

    def m(i: int, sid: str, when: str, winner: str = "team1") -> dict[str, Any]:
        return {
            "id": str(uuid4()),
            "session_id": sid,
            "type": "double",
            "team1_player_ids": [ball["id"], bank["id"]],
            "team2_player_ids": [bam["id"], bow["id"]],
            "winner": winner,
            "status": "completed",
            "elo_delta_team1": 0,
            "elo_delta_team2": 0,
            "created_at": f"{when}T12:{i:02d}:00Z",
            "updated_at": f"{when}T12:{i:02d}:30Z",
        }

    fake = MiniSupabase(
        {
            "players": [ball, bank, bam, bow],
            "sessions": [night, old],
            "matches": [m(i, night["id"], "2026-12-02") for i in range(3)]
            + [m(i, old["id"], "2026-10-01") for i in range(5)],
            "checkins": [
                {
                    "id": str(uuid4()),
                    "session_id": night["id"],
                    "player_id": p["id"],
                    "checkin_time": "2026-12-02T11:00:00Z",
                    "checkout_time": None,
                }
                for p in (ball, bank, bam, bow)
            ],
            "quest_settings": [
                {"id": 1, "start_date": "2026-12-01", "monthly_target": 20, "synced_key": None}
            ],
            "player_badges": [],
            "admins": [],
        }
    )
    app.dependency_overrides[get_supabase] = lambda: fake
    quest_store.invalidate()
    yield fake
    app.dependency_overrides.pop(get_supabase, None)
    quest_store.invalidate()


def pid(db: MiniSupabase, nickname: str) -> str:
    return next(str(p["id"]) for p in db.tables["players"] if p["nickname"] == nickname)


def test_profile_badges_count_from_the_start_date(client: TestClient, db: MiniSupabase) -> None:
    got = client.get(f"/api/quests/players/{pid(db, 'Ball')}").json()
    fire = next(q for q in got["quests"] if q["key"] == "fire")
    assert (
        fire["value"] == 3 and fire["levels"][0]["earned_at"] and not fire["levels"][1]["earned_at"]
    )
    aged = next(q for q in got["quests"] if q["key"] == "aged")
    assert aged["value"] == 3  # October's five games came before counting started
    assert {
        (r["badge"], r["level"])
        for r in db.tables["player_badges"]
        if r["player_id"] == pid(db, "Ball")
    } == {("fire", 1), ("revenge", 1), ("revenge", 2)}  # Bam: the most-faced, beaten 3 times
    assert client.get(f"/api/quests/players/{uuid4()}").status_code == 404


def test_line_shows_new_medals_once(client: TestClient, db: MiniSupabase) -> None:
    mine = client.get("/api/line/badges", headers=member()).json()
    assert sorted((u["badge"], u["level"]) for u in mine["unseen"]) == [
        ("fire", 1),
        ("revenge", 1),
        ("revenge", 2),
    ]
    assert (
        client.post(
            "/api/line/badges/seen", json={"items": mine["unseen"]}, headers=member()
        ).status_code
        == 204
    )
    assert client.get("/api/line/badges", headers=member()).json()["unseen"] == []
    assert client.get("/api/line/badges").status_code == 401


def test_a_corrected_result_takes_the_medal_back(client: TestClient, db: MiniSupabase) -> None:
    client.get(f"/api/quests/players/{pid(db, 'Ball')}")
    assert any(r["badge"] == "fire" for r in db.tables["player_badges"])
    # the second game was really a draw: the run is 1, then 1
    dec = [m for m in db.tables["matches"] if m["created_at"].startswith("2026-12-02")]
    dec[1]["winner"] = "draw"
    dec[1]["updated_at"] = "2026-12-03T00:00:00Z"
    quest_store.invalidate()
    client.get(f"/api/quests/players/{pid(db, 'Ball')}")
    assert not any(r["badge"] == "fire" for r in db.tables["player_badges"])


def test_top_and_recent(client: TestClient, db: MiniSupabase) -> None:
    top = client.get("/api/quests/top").json()
    # gold first, each quest once at its highest level
    assert [(b["badge"], b["level"]) for b in top[pid(db, "Ball")]] == [("revenge", 2), ("fire", 1)]
    # bronze isn't news: the feed starts at silver
    feed = client.get("/api/quests/recent").json()
    assert sorted((f["badge"], f["level"]) for f in feed if f["nickname"] == "Ball") == [
        ("revenge", 1),
        ("revenge", 2),
    ]
    assert all(f["badge"] != "fire" for f in feed)


def test_admin_settings_and_quests_off(client: TestClient, db: MiniSupabase) -> None:
    assert client.get("/api/admin/quests/settings").status_code == 401
    got = client.put(
        "/api/admin/quests/settings", json={"monthly_target": 2}, headers=admin()
    ).json()
    assert got["monthly_target"] == 2
    assert (
        client.put(
            "/api/admin/quests/settings", json={"monthly_target": 0}, headers=admin()
        ).status_code
        == 422
    )
    month = client.get(f"/api/quests/players/{pid(db, 'Ball')}").json()["month"]
    assert month["target"] == 2
    db.tables.pop("quest_settings")
    quest_store.invalidate()
    # switched off: quiet, not an error
    assert client.get(f"/api/quests/players/{pid(db, 'Ball')}").json() is None
    assert client.get("/api/quests/top").json() == {}
    assert client.get("/api/quests/recent").json() == []
    assert client.get("/api/admin/quests/settings", headers=admin()).json() is None
    assert (
        client.put(
            "/api/admin/quests/settings", json={"monthly_target": 5}, headers=admin()
        ).status_code
        == 503
    )


def test_badges_are_for_line_linked_members(client: TestClient, db: MiniSupabase) -> None:
    bank = pid(db, "Bank")
    # Bank won the same games as Ball, but hasn't linked LINE: counted, not shown
    got = client.get(f"/api/quests/players/{bank}").json()
    assert got["linked"] is False
    assert got["waiting"] == 2  # ไฟลุก and ล้างแค้น
    assert [(b["badge"], b["level"]) for b in got["waiting_top"]] == [("revenge", 2), ("fire", 1)]
    assert all(not lv["earned_at"] for q in got["quests"] for lv in q["levels"])
    assert all(q["value"] == 0 for q in got["quests"])
    assert bank not in client.get("/api/quests/top").json()
    assert all(f["player_id"] != bank for f in client.get("/api/quests/recent").json())
    assert client.get(f"/api/quests/players/{pid(db, 'Ball')}").json()["linked"] is True

    # Bank links LINE after those games: the medals are theirs at once, but
    # the home feed only announces what they win from then on
    line_id = "U" + "b" * 32
    next(p for p in db.tables["players"] if p["id"] == bank)["line_user_id"] = line_id
    db.tables["line_link_requests"] = [
        {
            "id": str(uuid4()),
            "line_user_id": line_id,
            "line_name": "Bank LINE",
            "player_id": bank,
            "status": "approved",
            "created_at": "2026-12-10T10:00:00Z",
            "decided_at": "2026-12-10T10:05:00Z",
        }
    ]
    quest_store.invalidate()
    got = client.get(f"/api/quests/players/{bank}").json()
    assert got["linked"] is True and got["waiting"] == 0
    fire = next(q for q in got["quests"] if q["key"] == "fire")
    assert fire["value"] == 3 and fire["levels"][0]["earned_at"]
    assert [b["badge"] for b in client.get("/api/quests/top").json()[bank]] == ["revenge", "fire"]
    assert all(f["player_id"] != bank for f in client.get("/api/quests/recent").json())


def test_line_invite_for_the_profile_nudge(client: TestClient, db: MiniSupabase) -> None:
    got = client.get("/api/quests/line-invite").json()
    assert got["url"] == "https://liff.line.me/1234567890-AbCdEfGh"
    assert got["qr_modules"]
