"""Niddeaw Pass: bought with credit by card holders, it runs 30 days and
gives the better side of the odds and two partner blocks a night. ELO is
not touched."""

import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "uxlab"))
from minisupabase import MiniSupabase

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token, create_line_token
from app.services import credit_card_service, line_checkin
from app.services import matchmaking_service as mm
from app.services.elo_service import expected_score

ADMIN_ID = str(uuid4())
SESSION_ID = str(uuid4())
NAMES = ["Ball", "Bank", "Faa", "Ton", "Oum", "Mew", "Tan", "Pee"]
LINE = {name: "U" + chr(ord("a") + i) * 32 for i, name in enumerate(NAMES)}


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


def member(name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_line_token(LINE[name], 'LINE name')}"}


@pytest.fixture
def db() -> Iterator[MiniSupabase]:
    players = [
        {
            "id": str(uuid4()),
            "nickname": n,
            "member_seq": i + 1,
            "elo_score": 1000,
            "elo_level": "beer",
            "is_active": True,
            "line_user_id": LINE[n],
            "created_at": "2026-01-01T00:00:00Z",
        }
        for i, n in enumerate(NAMES)
    ]
    fake = MiniSupabase(
        {
            "admins": [{"id": ADMIN_ID, "username": "admin"}],
            "players": players,
            "club_settings": [{"id": 1, "payment_method": "promptpay", "promptpay_id": "0812345678",
                               "promptpay_type": "phone", "default_court_fee_per_person": 80,
                               "default_shuttlecock_price_per_game": 29, "pass_price": 249}],
            "sessions": [{"id": SESSION_ID, "date": line_checkin._today().isoformat(), "location": "KB",
                          "status": "open", "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
                          "created_at": "2026-11-15T18:00:00Z"}],
            "checkins": [],
            "matches": [],
            "pairing_history": [],
            "locked_pairs": [],
            "credit_topups": [],
            "credit_ledger": [],
            "player_credits": [],
            "passes": [],
            "pass_blocks": [],
            "admin_activity_log": [],
        }
    )  # fmt: skip
    app.dependency_overrides[get_supabase] = lambda: fake
    credit_card_service.invalidate()
    yield fake
    app.dependency_overrides.pop(get_supabase, None)
    credit_card_service.invalidate()


@pytest.fixture
def client(db: MiniSupabase) -> TestClient:
    return TestClient(app)


def pid(db: MiniSupabase, name: str) -> str:
    return str(next(p["id"] for p in db.tables["players"] if p["nickname"] == name))


def card(db: MiniSupabase, name: str, credits: int = 1000) -> None:
    """They bought a pack through LINE: a card while the credit lasts."""
    top = str(uuid4())
    db.tables["credit_topups"].append(
        {
            "id": top,
            "player_id": pid(db, name),
            "status": "approved",
            "credits": credits,
            "price": credits,
            "created_at": "2026-11-01T00:00:00Z",
        }
    )
    db.tables["credit_ledger"].append(
        {
            "id": str(uuid4()),
            "player_id": pid(db, name),
            "delta": credits,
            "balance_after": credits,
            "kind": "topup",
            "ref_id": top,
            "created_at": "2026-11-01T00:00:00Z",
        }
    )
    db.tables["player_credits"].append({"player_id": pid(db, name), "balance": credits})
    credit_card_service.invalidate()


def check_in(db: MiniSupabase, *names: str) -> None:
    for n in names:
        db.tables["checkins"].append(
            {
                "id": str(uuid4()),
                "session_id": SESSION_ID,
                "player_id": pid(db, n),
                "checkin_time": "2026-11-15T18:05:00Z",
                "checkout_time": None,
            }
        )


def test_only_a_card_holder_can_buy_and_it_runs_thirty_days(
    client: TestClient, db: MiniSupabase
) -> None:
    refused = client.post("/api/line/pass/buy", headers=member("Ball"))
    assert refused.status_code == 403

    card(db, "Ball")
    before = datetime.now(UTC)
    got = client.post("/api/line/pass/buy", headers=member("Ball"))
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["balance"] == 1000 - 249
    ends = datetime.fromisoformat(body["ends_at"])
    assert timedelta(days=29, hours=23) < ends - before <= timedelta(days=30, minutes=1)
    assert db.tables["credit_ledger"][-1]["kind"] == "pass"

    # buying again while it runs adds the days on the end
    again = client.post("/api/line/pass/buy", headers=member("Ball")).json()
    assert datetime.fromisoformat(again["ends_at"]) - ends == timedelta(days=30)
    assert again["balance"] == 1000 - 2 * 249


def test_not_enough_credit_buys_nothing(client: TestClient, db: MiniSupabase) -> None:
    card(db, "Bank")
    db.tables["player_credits"][-1]["balance"] = 100
    res = client.post("/api/line/pass/buy", headers=member("Bank"))
    assert res.status_code == 409
    assert db.tables["passes"] == []


def test_the_price_is_the_admins_to_set(client: TestClient, db: MiniSupabase) -> None:
    res = client.put("/api/admin/settings", json={"pass_price": 199}, headers=admin())
    assert res.status_code == 200, res.text
    assert client.get("/api/line/pass", headers=member("Ball")).json()["price"] == 199
    assert (
        client.put("/api/admin/settings", json={"pass_price": 0}, headers=admin()).status_code
        == 422
    )


def test_two_blocks_a_night_from_who_is_in(client: TestClient, db: MiniSupabase) -> None:
    card(db, "Ball")
    client.post("/api/line/pass/buy", headers=member("Ball"))
    # not in tonight yet
    assert (
        client.post(
            "/api/line/pass/blocks", json={"player_id": pid(db, "Ton")}, headers=member("Ball")
        ).status_code
        == 409
    )
    check_in(db, "Ball", "Bank", "Faa", "Ton")
    state = client.get("/api/line/pass", headers=member("Ball")).json()
    assert state["checked_in"] and {c["nickname"] for c in state["candidates"]} == {
        "Bank",
        "Faa",
        "Ton",
    }

    for name in ("Ton", "Faa"):
        assert (
            client.post(
                "/api/line/pass/blocks", json={"player_id": pid(db, name)}, headers=member("Ball")
            ).status_code
            == 200
        )
    third = client.post(
        "/api/line/pass/blocks", json={"player_id": pid(db, "Bank")}, headers=member("Ball")
    )
    assert third.status_code == 409
    # someone not in tonight cannot be chosen
    assert client.post(
        "/api/line/pass/blocks", json={"player_id": pid(db, "Mew")}, headers=member("Ball")
    ).status_code in (404, 409)

    state = client.delete(f"/api/line/pass/blocks/{pid(db, 'Ton')}", headers=member("Ball")).json()
    assert [b["nickname"] for b in state["blocks"]] == ["Faa"]


def test_blocks_need_a_running_pass(client: TestClient, db: MiniSupabase) -> None:
    check_in(db, "Bank", "Ton")
    res = client.post(
        "/api/line/pass/blocks", json={"player_id": pid(db, "Ton")}, headers=member("Bank")
    )
    assert res.status_code == 403


def test_a_blocked_member_is_never_a_partner_but_can_be_across_the_net(
    client: TestClient, db: MiniSupabase
) -> None:
    card(db, "Ball")
    client.post("/api/line/pass/buy", headers=member("Ball"))
    check_in(db, *NAMES)
    for name in ("Bank", "Faa"):
        client.post(
            "/api/line/pass/blocks", json={"player_id": pid(db, name)}, headers=member("Ball")
        )
    q = client.get(f"/api/admin/matchmaking/queue?session_id={SESSION_ID}", headers=admin()).json()
    ball = pid(db, "Ball")
    for s in q["suggestions"]:
        for team in (s["team1_player_ids"], s["team2_player_ids"]):
            if ball in team:
                assert not {pid(db, "Bank"), pid(db, "Faa")} & set(team)


def test_a_pass_holder_is_put_on_the_side_with_the_better_odds() -> None:
    """Even teams (1020 a side) are what the four would get without a pass;
    the holder instead gets the other 1040 beside them, about 56%."""
    ids = [uuid4() for _ in range(4)]
    holder = ids[0]
    scores = dict(zip(ids, [1040, 1040, 1000, 1000], strict=True))
    players = [mm.CheckedInPlayer(p, s) for p, s in scores.items()]

    splits, _ = mm.suggest_doubles_pairings(players, [], 1, pass_holders=frozenset({holder}))
    split = splits[0]
    mine, theirs = (
        (split.team1, split.team2) if holder in split.team1 else (split.team2, split.team1)
    )
    avg = lambda team: sum(scores[p] for p in team) / len(team)
    assert expected_score(avg(mine), avg(theirs)) >= mm.PASS_EDGE

    even, _ = mm.suggest_doubles_pairings(players, [], 1)
    assert even[0].elo_balance_score == 0


def test_the_first_group_does_not_take_what_the_holders_group_needs() -> None:
    """The lab's night: eight free, the holder the weakest, two partners
    blocked. Which four go first can leave the holder a foursome that only
    splits 50:50 or worse; looking one group ahead keeps the odds for them.
    Ties fall by the players' ids, so it is tried with many."""
    scores = [1002, 1042, 1078, 1118, 1162, 1202, 1238, 1278]
    rounds = [((0, 2), (1, 3)), ((4, 6), (5, 7)), ((0, 1), (2, 3)), ((4, 5), (6, 7))]
    for _ in range(40):
        ids = [uuid4() for _ in scores]
        holder = ids[0]
        elo = dict(zip(ids, scores, strict=True))
        players = [mm.CheckedInPlayer(p, s) for p, s in elo.items()]
        blocked = frozenset({frozenset({holder, ids[2]}), frozenset({holder, ids[3]})})
        history = [
            mm.PairHistoryEntry(
                UUID(r["player_a_id"]), UUID(r["player_b_id"]), str(r["relation"]), n
            )
            for n, (t1, t2) in enumerate(rounds, start=1)
            for r in mm.build_pairing_history_rows(
                tuple(ids[i] for i in t1), tuple(ids[i] for i in t2), n
            )
        ]
        splits, _ = mm.suggest_doubles_pairings(
            players, history, 5, pass_holders=frozenset({holder}), blocked_partners=blocked
        )
        mine = next(s for s in splits if holder in s.team1 or holder in s.team2)
        team, other = (mine.team1, mine.team2) if holder in mine.team1 else (mine.team2, mine.team1)
        odds = expected_score(sum(elo[p] for p in team) / 2, sum(elo[p] for p in other) / 2)
        assert odds >= mm.PASS_EDGE
        assert not {ids[2], ids[3]} & set(team)


def test_blocked_partners_can_still_face_each_other() -> None:
    ids = [uuid4() for _ in range(4)]
    holder, blocked, x, y = ids
    players = [mm.CheckedInPlayer(p, 1000) for p in ids]
    pair = frozenset({frozenset({holder, blocked})})
    splits, _ = mm.suggest_doubles_pairings(players, [], 1, blocked_partners=pair)
    s = splits[0]
    assert not ({holder, blocked} <= set(s.team1) or {holder, blocked} <= set(s.team2))
    assert set(s.team1) | set(s.team2) == {holder, blocked, x, y}


def _won(
    db: MiniSupabase, winners: list[str], losers: list[str], delta: int, when: datetime
) -> None:
    db.tables["matches"].append({
        "id": str(uuid4()), "session_id": SESSION_ID, "type": "double", "status": "completed",
        "team1_player_ids": winners, "team2_player_ids": losers, "winner": "team1",
        "elo_delta_team1": delta, "elo_delta_team2": -delta,
        "created_at": when.isoformat(), "updated_at": when.isoformat(),
    })  # fmt: skip


def test_pass_routes_are_for_linked_members(client: TestClient) -> None:
    assert client.get("/api/line/pass").status_code == 401
    stranger = {"Authorization": f"Bearer {create_line_token('U' + 'z' * 32, 'x')}"}
    assert client.get("/api/line/pass", headers=stranger).status_code == 403
