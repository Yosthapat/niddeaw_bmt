"""NIDDEAW CUP phase 2: groups drawn by lot, the day's match list and its
time estimate, hidden from players until published."""

import random
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import tournament_draw as td
from tests import test_tournament as base
from tests.test_tournament import (
    BOTH,
    CLUB_ONLY,
    DETAILS,
    PARTNER,
    level_id,
    member,
    open_tournament,
    pid,
)

# the same in-memory club and client as the phase 1 tests
db = base.db
client = base.client


# --- the pure parts ------------------------------------------------------------


@pytest.mark.parametrize(
    "n,sizes",
    [
        (16, [4, 4, 4, 4]),
        (24, [4] * 6),
        (32, [4] * 8),
        (14, [4, 4, 3, 3]),
        (13, [4, 3, 3, 3]),
        (10, [4, 3, 3]),
        (5, [3, 2]),
        (2, [2]),
    ],
)
def test_groups_are_four_then_as_even_as_can_be(n: int, sizes: list[int]) -> None:
    assert td.group_sizes(n) == sizes


def test_the_draw_places_everyone_once() -> None:
    ids = [str(i) for i in range(14)]
    placed = td.draw(ids, random.Random(7))
    assert sorted(placed) == sorted(ids)
    assert len(set(placed.values())) == 14
    counts: dict[str, int] = {}
    for g, _ in placed.values():
        counts[g] = counts.get(g, 0) + 1
    assert counts == {"A": 4, "B": 4, "C": 3, "D": 3}


def test_the_draw_is_by_lot() -> None:
    ids = [str(i) for i in range(16)]
    assert td.draw(ids, random.Random(1)) != td.draw(ids, random.Random(2))


def test_seeds_meet_as_late_as_possible() -> None:
    assert td.seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    # the spec's round of 16 for a 24-team level: 1-16, 8-9, 4-13, 5-12 / 2-15, 7-10, 3-14, 6-11
    assert td.seed_order(16) == [1, 16, 8, 9, 4, 13, 5, 12, 2, 15, 7, 10, 3, 14, 6, 11]


def _level(max_teams: int, cut: bool = False) -> dict[str, Any]:
    return {"id": "L", "name": "x", "max_teams": max_teams, "cut_24": cut, "sort": 0}


def test_full_16_and_32_play_the_cross_group_pairs() -> None:
    assert td.first_slots(_level(16), 16, [4] * 4, "upper") == [
        "A1",
        "B2",
        "C1",
        "D2",
        "A2",
        "B1",
        "C2",
        "D1",
    ]
    assert td.first_slots(_level(16), 16, [4] * 4, "lower") == [
        "A3",
        "B4",
        "C3",
        "D4",
        "A4",
        "B3",
        "C4",
        "D3",
    ]
    assert td.first_slots(_level(32), 32, [4] * 8, "upper")[8:] == [
        "E1",
        "F2",
        "G1",
        "H2",
        "E2",
        "F1",
        "G2",
        "H1",
    ]


def test_24_teams_go_16_up_8_down_or_8_and_8_with_the_cut() -> None:
    assert td.bracket_counts(_level(24), 24, [4] * 6) == (16, 8)
    assert td.bracket_counts(_level(24, cut=True), 24, [4] * 6) == (8, 8)
    assert td.first_slots(_level(24), 24, [4] * 6, "upper")[:4] == ["U1", "U16", "U8", "U9"]
    assert td.first_slots(_level(24), 24, [4] * 6, "lower") == [
        "L1",
        "L8",
        "L4",
        "L5",
        "L2",
        "L7",
        "L3",
        "L6",
    ]


def test_a_level_not_full_gives_the_top_seeds_byes() -> None:
    # 14 teams: groups 4+4+3+3 -> 8 up, 6 down; the lower bracket of 8 has two byes
    assert td.bracket_counts(_level(16), 14, [4, 4, 3, 3]) == (8, 6)
    lower = td.first_slots(_level(16), 14, [4, 4, 3, 3], "lower")
    assert lower == ["L1", None, "L4", "L5", "L2", None, "L3", "L6"]
    rounds = td.knockout("L", lower, "lower")
    assert [len(r) for r in rounds] == [2, 2, 1]  # the byes play no first-round match


def _teams(level: str, n: int) -> list[dict[str, Any]]:
    placed = td.draw([f"{level}{i}" for i in range(n)], random.Random(3))
    return [{"id": tid, "group_label": g, "group_pos": p} for tid, (g, p) in placed.items()]


@pytest.mark.parametrize(
    "max_teams,cut,count",
    [(16, False, 38), (24, False, 58), (24, True, 50), (32, False, 78)],
)
def test_the_match_count_of_each_format(max_teams: int, cut: bool, count: int) -> None:
    lv = {**_level(max_teams, cut), "id": "L"}
    planned = td.plan([lv], {"L": _teams("L", max_teams)})
    assert len(planned) == count
    assert [m.match_no for m in planned] == list(range(1, count + 1))
    # every group match comes before any knockout match
    stages = [m.stage for m in planned]
    assert stages == sorted(stages, key=lambda s: 0 if s == "group" else 1)
    # a winner's slot always names an earlier match
    for m in planned:
        for slot in (m.slot_a, m.slot_b):
            if slot.startswith("W"):
                assert int(slot[1:]) < m.match_no


def test_levels_take_turns_round_by_round() -> None:
    levels = [{**_level(16), "id": "A", "sort": 0}, {**_level(16), "id": "B", "sort": 1}]
    planned = td.plan(levels, {"A": _teams("A", 16), "B": _teams("B", 16)})
    firsts = [(m.level_id, m.round) for m in planned if m.stage == "group"]
    assert firsts[:8] == [("A", 1)] * 8 and firsts[8:16] == [("B", 1)] * 8


def test_the_estimate_keeps_courts_rest_and_order() -> None:
    lv = {**_level(16), "id": "L"}
    planned = td.plan([lv], {"L": _teams("L", 16)})
    first = datetime(2026, 12, 20, 9, 0, tzinfo=td.CLUB_TZ)
    end = td.estimate(planned, first, courts=4, group_minutes=20, ko_minutes=30, rest_minutes=10)
    length = {m.key: timedelta(minutes=20 if m.stage == "group" else 30) for m in planned}
    spans = [(m.est_start, m.est_start + length[m.key], m) for m in planned if m.est_start]
    # never more matches at once than courts
    for start, _, _ in spans:
        assert sum(1 for s, e, _ in spans if s <= start < e) <= 4
    # a team rests at least 10 minutes between its matches
    by_team: dict[str, list[tuple[datetime, datetime]]] = {}
    for s, e, m in spans:
        for t in (m.team_a, m.team_b):
            if t:
                by_team.setdefault(t, []).append((s, e))
    for spells in by_team.values():
        spells.sort()
        for (_, e1), (s2, _) in zip(spells, spells[1:]):
            assert s2 >= e1 + timedelta(minutes=10)
    # the knockout starts after the last group match, plus the rest
    group_end = max(e for _, e, m in spans if m.stage == "group")
    assert min(s for s, _, m in spans if m.stage == "ko") >= group_end + timedelta(minutes=10)
    assert end == max(e for _, e, _ in spans)


# --- through the API -------------------------------------------------------------


def _fill(
    client: TestClient, db: Any, t: dict[str, Any], level: str, pairs: list[tuple[int, int]]
) -> None:
    for n, (a, b) in enumerate(pairs):
        got = client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/teams",
            json={
                "level_id": level_id(t, level),
                "team_name": f"ทีม {level} {n}",
                "captain": {**DETAILS, "player_id": pid(db, a)},
                "partner": {**PARTNER, "player_id": pid(db, b)},
                "paid_via": "cash",
            },
            headers=BOTH,
        )
        assert got.status_code == 201, got.text


def _ready(client: TestClient, db: Any) -> dict[str, Any]:
    t = open_tournament(client)
    _fill(client, db, t, "Soju ขึ้นไป", [(i, i + 1) for i in range(0, 32, 2)])  # 16 pairs
    client.patch(f"/api/admin/tournament/tournaments/{t['id']}", json={"courts": 6}, headers=BOTH)
    return t


def _draw(client: TestClient, t: dict[str, Any], level: str = "Soju ขึ้นไป") -> dict[str, Any]:
    got = client.post(
        f"/api/admin/tournament/tournaments/{t['id']}/levels/{level_id(t, level)}/draw",
        headers=BOTH,
    )
    assert got.status_code == 200, got.text
    return dict(got.json())


def test_draw_then_schedule_then_publish(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    state = _draw(client, t)
    soju = next(lv for lv in state["levels"] if lv["level"]["name"] == "Soju ขึ้นไป")
    assert soju["groups"] == ["A", "B", "C", "D"]
    assert sorted((x["group_label"], x["group_pos"]) for x in soju["teams"]) == [
        (g, p) for g in "ABCD" for p in range(1, 5)
    ]

    made = client.post(f"/api/admin/tournament/tournaments/{t['id']}/schedule", headers=BOTH)
    assert made.status_code == 200, made.text
    matches = made.json()["matches"]
    assert len(matches) == 38
    assert matches[0]["a"]["team_name"] and matches[0]["est_start"]
    assert matches[-1]["stage"] == "ko" and matches[-1]["a"]["slot"].startswith("W")
    assert made.json()["est_end"]

    # nothing public until published: the pages say "coming soon"
    public = client.get("/api/tournament").json()
    assert public["schedule_published"] is False and public["matches"] == []
    assert all(lv["groups"] == [] for lv in public["levels"])

    assert (
        client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/publish", json={"on": True}, headers=BOTH
        ).status_code
        == 200
    )
    public = client.get("/api/tournament").json()
    assert public["schedule_published"] is True and len(public["matches"]) == 38
    # each side shows its players' nicknames and avatars, never their real names
    first = public["matches"][0]
    assert [len(first[side]["players"]) for side in ("a", "b")] == [2, 2]
    assert all(p["nickname"].startswith("P") for p in first["a"]["players"])
    text = client.get("/api/tournament").text
    for private in (DETAILS["first_name"], DETAILS["last_name"], PARTNER["phone"]):
        assert private not in text
    soju_public = next(lv for lv in public["levels"] if lv["name"] == "Soju ขึ้นไป")

    assert [g["label"] for g in soju_public["groups"]] == ["A", "B", "C", "D"]
    # the LINE page reads the same
    seen = client.get("/api/line/tournament", headers=member(0)).json()
    assert seen["tournament"]["schedule_published"] is True


def test_only_confirmed_teams_are_drawn(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    # one more pair, signed up from LINE but not paid
    client.post(
        "/api/line/tournament/team",
        json={
            **DETAILS,
            "partner_id": pid(db, 33),
            "level_id": level_id(t, "Soju ขึ้นไป"),
            "team_name": "ยังไม่จ่าย",
        },
        headers=member(32),
    )
    soju = next(lv for lv in _draw(client, t)["levels"] if lv["level"]["name"] == "Soju ขึ้นไป")
    assert soju["confirmed"] == 16 and len(soju["teams"]) == 16
    assert "ยังไม่จ่าย" not in [x["name"] for x in soju["teams"]]


def test_moving_a_team_swaps_places(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    teams = next(lv for lv in _draw(client, t)["levels"] if lv["level"]["name"] == "Soju ขึ้นไป")[
        "teams"
    ]
    a1 = next(x for x in teams if (x["group_label"], x["group_pos"]) == ("A", 1))
    b2 = next(x for x in teams if (x["group_label"], x["group_pos"]) == ("B", 2))
    got = client.put(
        f"/api/admin/tournament/teams/{a1['id']}/group",
        json={"group_label": "B", "group_pos": 2},
        headers=BOTH,
    )
    assert got.status_code == 200, got.text
    after = {x["id"]: (x["group_label"], x["group_pos"]) for x in next(
        lv for lv in got.json()["levels"] if lv["level"]["name"] == "Soju ขึ้นไป"
    )["teams"]}  # fmt: skip
    assert after[a1["id"]] == ("B", 2) and after[b2["id"]] == ("A", 1)


def test_the_match_list_locks_the_groups_until_cleared(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    _draw(client, t)
    url = f"/api/admin/tournament/tournaments/{t['id']}"
    client.post(f"{url}/schedule", headers=BOTH)
    again = client.post(f"{url}/levels/{level_id(t, 'Soju ขึ้นไป')}/draw", headers=BOTH)
    assert again.status_code == 409
    assert client.post(f"{url}/schedule", headers=BOTH).status_code == 409
    client.post(f"{url}/publish", json={"on": True}, headers=BOTH)
    assert (
        client.delete(f"{url}/schedule", headers=BOTH).status_code == 409
    )  # published: hide first
    client.post(f"{url}/publish", json={"on": False}, headers=BOTH)
    assert client.delete(f"{url}/schedule", headers=BOTH).status_code == 200
    assert (
        client.post(f"{url}/levels/{level_id(t, 'Soju ขึ้นไป')}/draw", headers=BOTH).status_code
        == 200
    )


def test_a_schedule_needs_courts_and_every_team_placed(db: Any, client: TestClient) -> None:
    t = open_tournament(client)
    _fill(client, db, t, "Soju ขึ้นไป", [(0, 1), (2, 3), (4, 5)])
    url = f"/api/admin/tournament/tournaments/{t['id']}"
    assert client.post(f"{url}/schedule", headers=BOTH).status_code == 400  # no courts
    client.patch(url, json={"courts": 2}, headers=BOTH)
    got = client.post(f"{url}/schedule", headers=BOTH)
    assert got.status_code == 409 and "ไม่มีกลุ่ม" in got.json()["detail"]
    _draw(client, t)
    made = client.post(f"{url}/schedule", headers=BOTH).json()
    # three teams: one group, three matches, then a final up top (two up, one down)
    assert [m["stage"] for m in made["matches"]] == ["group"] * 3 + ["ko"]


def test_the_day_starts_when_the_admin_says(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    client.patch(
        f"/api/admin/tournament/tournaments/{t['id']}", json={"day_start": "08:30"}, headers=BOTH
    )
    _draw(client, t)
    made = client.post(f"/api/admin/tournament/tournaments/{t['id']}/schedule", headers=BOTH).json()
    first = datetime.fromisoformat(made["matches"][0]["est_start"])
    assert first.astimezone(td.CLUB_TZ).strftime("%Y-%m-%d %H:%M") == "2026-12-20 08:30"


def test_a_club_only_admin_reaches_none_of_it(db: Any, client: TestClient) -> None:
    t = _ready(client, db)
    assert (
        client.get(
            f"/api/admin/tournament/tournaments/{t['id']}/draw", headers=CLUB_ONLY
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/tournament/tournaments/{t['id']}/schedule", headers=CLUB_ONLY
        ).status_code
        == 403
    )
