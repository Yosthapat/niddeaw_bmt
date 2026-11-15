"""NIDDEAW CUP phase 3: calling matches to courts, results and their rules,
the group tables, the knockout filled and moved on, and shuttle coupons."""

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import tournament_play as tp
from app.services import tournament_service as ts
from tests import test_tournament as base
from tests.test_tournament import BOTH, DETAILS, PARTNER, open_tournament
from tests.test_tournament_schedule import _draw, _fill

db = base.db
client = base.client


# --- the score rules ------------------------------------------------------------


@pytest.mark.parametrize(
    "sets,winner",
    [([[21, 15], [21, 19]], "a"), ([[21, 15], [18, 21]], "draw"), ([[0, 21], [20, 21]], "b")],
)
def test_group_scores(sets: list[list[int]], winner: str) -> None:
    assert tp.judge("group", sets) == winner


@pytest.mark.parametrize(
    "sets",
    [[[22, 20], [21, 10]], [[21, 21], [21, 10]], [[21, 10]], [[21, 10], [21, 10], [21, 10]]],
)
def test_group_scores_that_cannot_be(sets: list[list[int]]) -> None:
    with pytest.raises(tp.BadScore):
        tp.judge("group", sets)


@pytest.mark.parametrize(
    "sets,winner",
    [
        ([[21, 19], [21, 5]], "a"),
        ([[22, 20], [19, 21], [30, 29]], "a"),
        ([[10, 21], [28, 30]], "b"),
    ],
)
def test_knockout_scores(sets: list[list[int]], winner: str) -> None:
    assert tp.judge("ko", sets) == winner


@pytest.mark.parametrize(
    "sets",
    [
        [[21, 20], [21, 5]],  # needs two clear
        [[30, 27], [21, 5]],  # 30 only from 28 or 29
        [[21, 5], [5, 21]],  # 1–1 needs a third
        [[21, 5], [21, 5], [21, 5]],  # already won
    ],
)
def test_knockout_scores_that_cannot_be(sets: list[list[int]]) -> None:
    with pytest.raises(tp.BadScore):
        tp.judge("ko", sets)


def _m(a: str, b: str, sets: list[list[int]], winner: str) -> dict[str, Any]:
    return {"team_a": a, "team_b": b, "sets": sets, "winner": winner}


def test_the_table_and_its_tie_breaks() -> None:
    done = [
        _m("w", "x", [[21, 10], [21, 10]], "a"),  # w 2 pts
        _m("y", "z", [[21, 19], [19, 21]], "draw"),  # y, z 1 pt
        _m("w", "y", [[21, 15], [15, 21]], "draw"),  # w 3, y 2
        _m("x", "z", [[21, 0], [21, 0]], "a"),  # x 2
        _m("w", "z", [[10, 21], [10, 21]], "b"),  # w 3, z 3
        _m("x", "y", [[21, 5], [5, 21]], "draw"),  # x 3, y 3
    ]
    table = tp.standings(["w", "x", "y", "z"], done)
    # all on 3 points: x +20 first, z -20 last; w and y both level at 0,
    # so points scored decide (y 102, w 98)
    assert [r.team_id for r in table] == ["x", "y", "w", "z"]
    assert [r.points for r in table] == [3, 3, 3, 3]
    assert [r.diff for r in table] == [20, 0, 0, -20]
    assert [r.rank for r in table] == [1, 2, 3, 4]


def test_head_to_head_settles_a_dead_heat() -> None:
    # "z" and "a" end level on everything; z beat a, so z goes above it
    done = [
        _m("z", "a", [[21, 19], [21, 19]], "a"),
        _m("r", "z", [[21, 19], [21, 19]], "a"),
        _m("a", "s", [[21, 19], [21, 19]], "a"),
    ]
    table = tp.standings(["a", "r", "s", "z"], done)
    z, a = next(r for r in table if r.team_id == "z"), next(r for r in table if r.team_id == "a")
    assert (z.points, z.diff, z.scored, z.conceded) == (a.points, a.diff, a.scored, a.conceded)
    assert [r.team_id for r in table] == ["r", "z", "a", "s"]


def _row(team: str, group: str, rank: int, points: int, diff: int = 0) -> tp.Row:
    r = tp.Row(
        team_id=team, group=group, rank=rank, played=3, points=points, scored=60 + diff, conceded=60
    )
    return r


def _tables(groups: int, size: int = 4) -> dict[str, list[tp.Row]]:
    out = {}
    for g in "ABCDEFGH"[:groups]:
        out[g] = [_row(f"{g}{r}", g, r, 8 - 2 * r, diff=ord(g)) for r in range(1, size + 1)]
    return out


def test_24_teams_seed_16_up_with_the_best_thirds() -> None:
    lv = {"max_teams": 24, "cut_24": False}
    slots, tiers = tp.seeds(lv, _tables(6))
    upper = [slots[f"U{i}"] for i in range(1, 17)]
    lower = [slots[f"L{i}"] for i in range(1, 9)]
    assert {t[1] for t in upper[:6]} == {"1"} and {t[1] for t in upper[6:12]} == {"2"}
    assert {t[1] for t in upper[12:]} == {"3"} and len(upper[12:]) == 4
    assert [t[1] for t in lower] == ["3", "3"] + ["4"] * 6
    # within a tier, the better record first (here group F has the best difference)
    assert upper[0] == "F1" and tiers["U1"] == 1


def test_24_teams_with_the_cut_seed_8_and_8() -> None:
    slots, _ = tp.seeds({"max_teams": 24, "cut_24": True}, _tables(6))
    assert len([k for k in slots if k.startswith("U")]) == 8
    assert len([k for k in slots if k.startswith("L")]) == 8
    assert [slots[f"L{i}"][1] for i in range(1, 9)] == ["2"] * 4 + ["3"] * 4


def test_group_mates_are_kept_apart_in_the_first_round() -> None:
    slots = {"U1": "a1", "U2": "b1", "U3": "c2", "U4": "a2"}
    tiers = {"U1": 1, "U2": 1, "U3": 2, "U4": 2}
    group_of = {"a1": "A", "a2": "A", "b1": "B", "c2": "C"}
    pairs = [("U1", "U4"), ("U2", "U3")]  # a1 v a2 clashes
    fixed = tp.keep_apart(pairs, slots, tiers, group_of)
    assert group_of[fixed["U1"]] != group_of[fixed["U4"]]
    assert group_of[fixed["U2"]] != group_of[fixed["U3"]]


# --- through the API -------------------------------------------------------------


def _ready_day(client: TestClient, db: Any) -> dict[str, Any]:
    t = open_tournament(client)
    _fill(client, db, t, "Soju ขึ้นไป", [(i, i + 1) for i in range(0, 32, 2)])
    client.patch(f"/api/admin/tournament/tournaments/{t['id']}", json={"courts": 4}, headers=BOTH)
    _draw(client, t)
    assert (
        client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/schedule", headers=BOTH
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/publish", json={"on": True}, headers=BOTH
        ).status_code
        == 200
    )
    return t


def _day(client: TestClient, t: dict[str, Any]) -> dict[str, Any]:
    got = client.get(f"/api/admin/tournament/tournaments/{t['id']}/day", headers=BOTH)
    assert got.status_code == 200, got.text
    return dict(got.json())


def _play(client: TestClient, m: dict[str, Any], sets: list[list[int]], court: int = 1) -> Any:
    called = client.post(
        f"/api/admin/tournament/matches/{m['id']}/call", json={"court": court}, headers=BOTH
    )
    assert called.status_code == 200, called.text
    return client.post(
        f"/api/admin/tournament/matches/{m['id']}/result",
        json={"sets": sets, "shuttles": 2},
        headers=BOTH,
    )


def test_nothing_is_called_before_the_list_is_published(db: Any, client: TestClient) -> None:
    t = open_tournament(client)
    _fill(client, db, t, "Soju ขึ้นไป", [(0, 1), (2, 3), (4, 5), (6, 7)])
    client.patch(f"/api/admin/tournament/tournaments/{t['id']}", json={"courts": 2}, headers=BOTH)
    _draw(client, t)
    client.post(f"/api/admin/tournament/tournaments/{t['id']}/schedule", headers=BOTH)
    first = _day(client, t)["matches"][0]
    got = client.post(
        f"/api/admin/tournament/matches/{first['id']}/call", json={"court": 1}, headers=BOTH
    )
    assert got.status_code == 409


def test_calling_to_courts(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    day = _day(client, t)
    m1, m2 = day["matches"][0], day["matches"][1]
    assert m1["id"] in day["ready"]
    url = "/api/admin/tournament/matches"
    assert client.post(f"{url}/{m1['id']}/call", json={"court": 1}, headers=BOTH).status_code == 200
    assert (
        client.post(f"{url}/{m2['id']}/call", json={"court": 1}, headers=BOTH).status_code == 409
    )  # court taken
    assert (
        client.post(f"{url}/{m2['id']}/call", json={"court": 9}, headers=BOTH).status_code == 400
    )  # 4 courts
    again = client.post(f"{url}/{m1['id']}/call-again", headers=BOTH).json()
    m1_now = next(m for m in again["matches"] if m["id"] == m1["id"])
    assert (m1_now["status"], m1_now["court"], m1_now["call_count"]) == ("on_court", 1, 2)
    # a team on court can't be called elsewhere
    same_team = next(
        m
        for m in again["matches"][2:]
        if {m["a"]["team_id"], m["b"]["team_id"]} & {m1["a"]["team_id"], m1["b"]["team_id"]}
    )
    assert (
        client.post(f"{url}/{same_team['id']}/call", json={"court": 2}, headers=BOTH).status_code
        == 409
    )
    back = client.post(f"{url}/{m1['id']}/uncall", headers=BOTH).json()
    assert next(m for m in back["matches"] if m["id"] == m1["id"])["status"] == "scheduled"


def test_a_result_needs_a_score_the_rules_allow(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    m = _day(client, t)["matches"][0]
    url = f"/api/admin/tournament/matches/{m['id']}"
    client.post(f"{url}/call", json={"court": 1}, headers=BOTH)
    bad = client.post(f"{url}/result", json={"sets": [[22, 20], [21, 5]]}, headers=BOTH)
    assert bad.status_code == 400 and "ดิวส์" in bad.json()["detail"]
    ok = client.post(
        f"{url}/result", json={"sets": [[21, 15], [21, 19]], "shuttles": 3}, headers=BOTH
    )
    done = next(x for x in ok.json()["matches"] if x["id"] == m["id"])
    assert (done["status"], done["winner"], done["court"], done["shuttles"]) == (
        "done",
        "a",
        None,
        3,
    )
    # each side gave a coupon a shuttle
    used = {c["team_id"]: c["used"] for c in ok.json()["coupons"]}
    assert used[m["a"]["team_id"]] == 3 and used[m["b"]["team_id"]] == 3


def test_a_team_rests_before_it_is_ready_again(
    db: Any, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = _ready_day(client, db)
    day = _day(client, t)
    m = day["matches"][0]
    after = _play(client, m, [[21, 10], [21, 10]]).json()
    team = m["a"]["team_id"]
    theirs = [
        x
        for x in after["matches"]
        if x["status"] == "scheduled" and team in (x["a"]["team_id"], x["b"]["team_id"])
    ]
    assert theirs and theirs[0]["id"] not in after["ready"]
    later = ts.now() + timedelta(minutes=11)
    monkeypatch.setattr(ts, "now", lambda: later)
    assert theirs[0]["id"] in _day(client, t)["ready"]


def _play_groups(client: TestClient, t: dict[str, Any]) -> dict[str, Any]:
    day = _day(client, t)
    for m in [x for x in day["matches"] if x["stage"] == "group"]:
        got = _play(client, m, [[21, 10], [21, 12]])
        assert got.status_code == 200, got.text
    return _day(client, t)


def test_the_groups_fill_the_knockout_and_winners_move_on(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    day = _play_groups(client, t)
    public = client.get("/api/tournament").json()
    soju = next(lv for lv in public["levels"] if lv["name"] == "Soju ขึ้นไป")
    first_of = {g["label"]: g["standings"][0]["team_id"] for g in soju["groups"]}
    second_of = {g["label"]: g["standings"][1]["team_id"] for g in soju["groups"]}
    ko = [m for m in day["matches"] if m["stage"] == "ko"]
    opener = next(m for m in ko if m["a"]["slot"] == "A1")
    assert opener["a"]["team_id"] == first_of["A"] and opener["b"]["team_id"] == second_of["B"]
    assert all(m["a"]["team_id"] for m in ko if m["round"] == 8)

    # a quarter-final won moves its winner into the semi
    _play(client, opener, [[21, 10], [21, 10]])
    semi = next(
        m
        for m in _day(client, t)["matches"]
        if f"W{opener['match_no']}" in (m["a"]["slot"], m["b"]["slot"])
    )
    side = "a" if semi["a"]["slot"] == f"W{opener['match_no']}" else "b"
    assert semi[side]["team_id"] == first_of["A"]


def test_a_result_is_fixed_once_what_it_decides_is_called(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    day = _play_groups(client, t)
    last_group = [m for m in day["matches"] if m["stage"] == "group"][-1]
    url = "/api/admin/tournament/matches"
    # still free to correct: nothing in the knockout has started
    fix = client.post(
        f"{url}/{last_group['id']}/result", json={"sets": [[21, 18], [21, 18]]}, headers=BOTH
    )
    assert fix.status_code == 200
    opener = next(m for m in fix.json()["matches"] if m["stage"] == "ko" and m["a"]["team_id"])
    client.post(f"{url}/{opener['id']}/call", json={"court": 1}, headers=BOTH)
    late = client.post(
        f"{url}/{last_group['id']}/result", json={"sets": [[21, 1], [21, 1]]}, headers=BOTH
    )
    assert late.status_code == 409


def test_a_walkover_counts_21_0_twice(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    m = _day(client, t)["matches"][0]
    got = client.post(
        f"/api/admin/tournament/matches/{m['id']}/result",
        json={"walkover_winner": "b"},
        headers=BOTH,
    )
    done = next(x for x in got.json()["matches"] if x["id"] == m["id"])
    assert (done["sets"], done["winner"], done["walkover"], done["shuttles"]) == (
        [[0, 21], [0, 21]],
        "b",
        True,
        0,
    )


def test_coupons_sold_and_bought_back(db: Any, client: TestClient) -> None:
    t = _ready_day(client, db)
    m = _day(client, t)["matches"][0]
    _play(client, m, [[21, 10], [21, 10]])
    team = m["a"]["team_id"]
    url = f"/api/admin/tournament/teams/{team}/coupons"
    sold = client.post(f"{url}/sell?quantity=1&paid_via=cash", headers=BOTH)
    assert sold.status_code == 200, sold.text
    mine = next(c for c in sold.json()["coupons"] if c["team_id"] == team)
    assert (mine["sets"], mine["given"], mine["used"], mine["left"]) == (2, 12, 2, 10)
    assert (
        client.post(f"{url}/return?quantity=11&paid_via=cash", headers=BOTH).status_code == 409
    )  # only 10 left
    back = client.post(f"{url}/return?quantity=10&paid_via=transfer", headers=BOTH)
    assert next(c for c in back.json()["coupons"] if c["team_id"] == team)["left"] == 0
    assert (
        client.post(f"{url}/sell?quantity=1&paid_via=cash", headers=BOTH).status_code == 409
    )  # returned: no more
    money = client.get(f"/api/admin/tournament/tournaments/{t['id']}/money", headers=BOTH).json()
    rows_ = {
        (x["category"], x["amount"])
        for x in money
        if x["team_id"] == team and x["category"] != "entry_fee"
    }
    assert rows_ == {("extra_shuttles", 450.0), ("coupon_refund", 700.0)}
    assert db.tables["other_income"] == [] and db.tables["expenses"] == []


def test_the_public_page_shows_results_and_tables_but_nothing_private(
    db: Any, client: TestClient
) -> None:
    t = _ready_day(client, db)
    m = _day(client, t)["matches"][0]
    _play(client, m, [[21, 10], [21, 12]])
    public = client.get("/api/tournament").json()
    shown = next(x for x in public["matches"] if x["id"] == m["id"])
    assert (shown["status"], shown["sets"], shown["winner"]) == ("done", [[21, 10], [21, 12]], "a")
    group = next(g for lv in public["levels"] for g in lv["groups"] if g["standings"])
    assert group["standings"][0]["points"] == 2
    text = client.get("/api/tournament").text
    for private in (DETAILS["first_name"], DETAILS["last_name"], PARTNER["phone"]):
        assert private not in text
