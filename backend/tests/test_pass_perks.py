# ruff: noqa: F811 — db and client are the shared fixtures from test_niddeaw_pass
"""Niddeaw Pass looks, the run of passes in a row that earns the loyal ones,
and the holder's own numbers and last night."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services import pass_perks
from tests.test_niddeaw_pass import (  # noqa: F401 — client, db: fixtures
    SESSION_ID,
    MiniSupabase,
    _won,
    client,
    db,
    member,
    pid,
)

NOW = datetime(2026, 11, 16, 12, tzinfo=UTC)


def span(start_days: float, length: float = 30) -> tuple[datetime, datetime]:
    start = NOW + timedelta(days=start_days)
    return start, start + timedelta(days=length)


def give_passes(db: MiniSupabase, name: str, *spans: tuple[datetime, datetime]) -> None:
    for start, end in spans:
        db.tables["passes"].append(
            {"id": str(uuid4()), "player_id": pid(db, name), "credits": 249,
             "starts_at": start.isoformat(), "ends_at": end.isoformat()}
        )  # fmt: skip


# ------------------------------------------------------------ in a row


def test_passes_back_to_back_count_up_and_a_gap_starts_again() -> None:
    three = [span(-80), span(-50), span(-20)]
    assert pass_perks.streak(three, NOW) == pass_perks.Streak(current=3, best=3)
    # a day between two passes breaks the run
    broken = [span(-81), span(-50), span(-20)]
    assert pass_perks.streak(broken, NOW) == pass_perks.Streak(current=2, best=2)
    # ran out: nothing current, but what was reached stays reached
    over = [span(-140), span(-110), span(-80)]
    assert pass_perks.streak(over, NOW) == pass_perks.Streak(current=0, best=3)


def test_earned_looks_follow_the_best_run() -> None:
    assert pass_perks.earned(2) == ([], [])
    assert pass_perks.earned(3) == (["moon"], [])
    assert pass_perks.earned(6) == (["moon", "king"], [])
    assert pass_perks.earned(12) == (["moon", "king", "legend"], ["diamond"])


# --------------------------------------------------------------- looks


def test_a_pass_look_needs_a_running_pass(client: TestClient, db: MiniSupabase) -> None:
    res = client.put("/api/line/pass/style", json={"frame": "gold"}, headers=member("Ball"))
    assert res.status_code == 403
    give_passes(db, "Ball", (datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=29)))
    res = client.put("/api/line/pass/style", json={"frame": "gold", "card": "foil"}, headers=member("Ball"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["frame"], body["card"]) == ("gold", "foil")
    assert body["frames_open"] == ["gold", "neon", "crown"]
    assert body["streak"] == 1
    # a loyal frame not earned yet
    assert client.put("/api/line/pass/style", json={"frame": "moon"}, headers=member("Ball")).status_code == 403
    # everyone sees it
    assert client.get("/api/pass-styles").json() == {pid(db, "Ball"): {"frame": "gold", "card": "foil"}}


def test_pass_looks_go_when_the_pass_ends_but_earned_ones_stay(client: TestClient, db: MiniSupabase) -> None:
    now = datetime.now(UTC)
    ball, faa = pid(db, "Ball"), pid(db, "Faa")
    # Ball: three passes in a row, all over now; Faa: one, over
    give_passes(db, "Ball", *[(now - timedelta(days=d), now - timedelta(days=d - 30)) for d in (100, 70, 40)])
    give_passes(db, "Faa", (now - timedelta(days=40), now - timedelta(days=10)))
    db.tables["pass_styles"] += [
        {"player_id": ball, "frame": "moon", "card": "foil"},
        {"player_id": faa, "frame": "gold", "card": None},
    ]
    assert client.get("/api/pass-styles").json() == {ball: {"frame": "moon", "card": None}}
    body = client.get("/api/line/pass", headers=member("Ball")).json()
    assert (body["streak"], body["best_streak"]) == (0, 3)
    assert body["frames_open"] == ["moon"]
    # and still settable with no pass
    assert client.put("/api/line/pass/style", json={"frame": "moon"}, headers=member("Ball")).status_code == 200


# --------------------------------------------------------- their numbers


def test_stats_and_night_are_for_a_running_pass(client: TestClient, db: MiniSupabase) -> None:
    assert client.get("/api/line/pass/stats", headers=member("Ball")).status_code == 403
    assert client.get("/api/line/pass/night", headers=member("Ball")).status_code == 403


def test_stats_find_the_partner_rival_and_form(client: TestClient, db: MiniSupabase) -> None:
    now = datetime.now(UTC)
    give_passes(db, "Ball", (now - timedelta(days=1), now + timedelta(days=29)))
    ball, bank, faa, ton, oum, tan, mew = (pid(db, n) for n in ("Ball", "Bank", "Faa", "Ton", "Oum", "Tan", "Mew"))
    # with Bank: 3 wins of 3 against Faa & Ton; then 3 losses of 3 (with Oum) to Tan & Mew
    t = now - timedelta(days=5)
    for i in range(3):
        _won(db, [ball, bank], [faa, ton], 10, t + timedelta(minutes=10 * i))
    for i in range(3):
        _won(db, [tan, mew], [ball, oum], 8, t + timedelta(minutes=40 + 10 * i))
    db.tables["players"][0]["elo_score"] = 1006  # 1000 + 30 - 24
    body = client.get("/api/line/pass/stats", headers=member("Ball")).json()
    assert body["games"] == 6
    assert body["partner"]["player"]["nickname"] == "Bank"
    assert (body["partner"]["wins"], body["partner"]["games"]) == (3, 3)
    assert body["rival"]["player"]["nickname"] in ("Tan", "Mew")
    assert body["rival"]["wins"] == 0
    assert body["last"] == ["W", "W", "W", "L", "L", "L"]
    assert body["best_streak"] == 3
    # worked back from now: 1006 after the last, 1000 before the first
    assert body["series"][-1]["elo"] == 1006
    assert body["series"][0]["elo"] == 1010
    assert sum(b["games"] for b in body["form"]) == 6


def test_night_sums_the_last_session(client: TestClient, db: MiniSupabase) -> None:
    now = datetime.now(UTC)
    give_passes(db, "Ball", (now - timedelta(days=1), now + timedelta(days=29)))
    ball, bank, faa, ton = (pid(db, n) for n in ("Ball", "Bank", "Faa", "Ton"))
    # an earlier night that doesn't count
    old = str(uuid4())
    db.tables["sessions"].append({"id": old, "date": "2026-11-01", "status": "closed", "location": "KB",
                                  "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
                                  "created_at": "2026-11-01T12:00:00Z"})  # fmt: skip
    _won(db, [ball, bank], [faa, ton], 7, now - timedelta(days=10))
    db.tables["matches"][-1]["session_id"] = old
    # tonight: an upset win with Bank (they were rated well above), then a loss
    db.tables["players"][2]["elo_score"] = 1400  # Faa
    db.tables["players"][3]["elo_score"] = 1400  # Ton
    _won(db, [ball, bank], [faa, ton], 16, now - timedelta(hours=2))
    _won(db, [faa, ton], [ball, bank], 4, now - timedelta(hours=1))
    db.tables["players"][0]["elo_score"] = 1019  # 1000 + 7 + 16 - 4
    body = client.get("/api/line/pass/night", headers=member("Ball")).json()
    assert body["nickname"] == "Ball"
    assert (body["games"], body["wins"], body["draws"]) == (2, 1, 0)
    assert (body["elo_before"], body["elo_after"]) == (1007, 1019)
    assert body["partner"]["player"]["nickname"] == "Bank"
    assert {p["nickname"] for p in body["upset"]["rivals"]} == {"Faa", "Ton"}
    assert body["upset"]["odds"] < 0.5
    assert SESSION_ID  # tonight is the fixture's night
