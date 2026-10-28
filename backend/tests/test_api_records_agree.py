"""Every page that shows a member's record shows the same one.

On 27 Oct 2026, 26 of the club's 97 members had a record on the members
list, their profile and the ranking that did not match their own match
history: Aekk read 10 games against 7 played. Those pages read counters on
the player row, and the counters had drifted. The match history read the
matches.

These tests load counters that are deliberately wrong next to matches that
say otherwise, and require every page to show what the matches say.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.security import create_access_token
from app.services import record_service
from tests.conftest import FakeSupabase

AEKK, BALL, CHAI = str(uuid4()), str(uuid4()), str(uuid4())
NIGHT = str(uuid4())


def member(pid: str, nickname: str, *, games: int, wins: int, draws: int, losses: int) -> dict[str, Any]:
    return {
        "id": pid,
        "nickname": nickname,
        "member_seq": 1,
        "avatar_url": None,
        "elo_score": 1200,
        "elo_level": "highball",
        "is_active": True,
        "line_id": None,
        "dominant_hand": None,
        "tiktok": None,
        "instagram": None,
        "quote": None,
        "created_at": "2026-10-01T10:00:00+00:00",
        "games": games,
        "wins": wins,
        "draws": draws,
        "losses": losses,
    }


def match(winner: str | None, *, status: str = "completed") -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "session_id": NIGHT,
        "type": "single",
        "team1_player_ids": [AEKK],
        "team2_player_ids": [BALL],
        "winner": winner,
        "status": status,
        "created_at": "2026-10-24T13:00:00+00:00",
        "updated_at": "2026-10-24T13:20:00+00:00",
        "elo_delta_team1": 8,
        "elo_delta_team2": -8,
        "match_no": 1,
    }


# What the counters claim (wrong), and what the matches say (right):
#   Aekk  counters 10 / 4 / 6 / 0   matches 7 / 4 / 3 / 0
#   Ball  counters  0 / 0 / 0 / 0   matches 7 / 0 / 3 / 4
#   Chai  counters  3 / 1 / 1 / 1   matches 0 — never played
TRUTH = {
    AEKK: {"games": 7, "wins": 4, "draws": 3, "losses": 0},
    BALL: {"games": 7, "wins": 0, "draws": 3, "losses": 4},
    CHAI: {"games": 0, "wins": 0, "draws": 0, "losses": 0},
}


@pytest.fixture
def club(supabase_rows: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    supabase_rows["players"] = [
        member(AEKK, "Aekk", games=10, wins=4, draws=6, losses=0),
        member(BALL, "Ball", games=0, wins=0, draws=0, losses=0),
        member(CHAI, "Chai", games=3, wins=1, draws=1, losses=1),
    ]
    matches = [match("team1") for _ in range(4)] + [match("draw") for _ in range(3)]
    # The fake does not filter, so the table and the numbered view hold the
    # same completed matches the real ones would return.
    supabase_rows["matches"] = matches
    supabase_rows["matches_numbered"] = matches
    supabase_rows["sessions"] = [{"id": NIGHT, "date": "2026-10-24"}]
    supabase_rows["seasons"] = []
    return supabase_rows


def record(stats: dict[str, Any]) -> dict[str, int]:
    return {k: stats[k] for k in ("games", "wins", "draws", "losses")}


def test_the_members_list_counts_the_matches(client: TestClient, club: Any) -> None:
    body = client.get("/api/players").json()
    assert {s["player"]["id"]: record(s) for s in body} == TRUTH


def test_the_name_lookup_counts_the_matches_too(client: TestClient, club: Any) -> None:
    body = client.get("/api/players", params={"ids": [AEKK, BALL]}).json()
    assert {s["player"]["id"]: record(s) for s in body} == {AEKK: TRUTH[AEKK], BALL: TRUTH[BALL], CHAI: TRUTH[CHAI]}


@pytest.mark.parametrize("pid", [AEKK, BALL, CHAI])
def test_a_profile_counts_the_matches(client: TestClient, club: Any, pid: str) -> None:
    # The fake ignores .eq("id", …) and hands back the first player row, so
    # put the one asked for first.
    club["players"].sort(key=lambda row: row["id"] != pid)
    assert record(client.get(f"/api/players/{pid}/profile").json()) == TRUTH[pid]


def test_the_all_time_ranking_counts_the_matches(client: TestClient, club: Any) -> None:
    body = client.get("/api/ranking", params={"period": "all"}).json()
    # Chai has played nothing, so is not on a ranking at all, whatever the
    # counter on the row says.
    assert {s["player"]["id"]: record(s) for s in body} == {AEKK: TRUTH[AEKK], BALL: TRUTH[BALL]}


def test_the_hall_of_fame_counts_the_matches(client: TestClient, club: Any) -> None:
    body = client.get("/api/hall-of-fame").json()
    assert {s["player"]["id"]: record(s) for s in body} == {AEKK: TRUTH[AEKK], BALL: TRUTH[BALL]}


def test_a_matchs_detail_counts_the_matches(client: TestClient, club: Any) -> None:
    detail = client.get(f"/api/matches/{club['matches'][0]['id']}/detail").json()
    assert record(detail["team1"][0]) == TRUTH[AEKK]
    assert record(detail["team2"][0]) == TRUTH[BALL]


def test_only_completed_matches_are_asked_for(club: Any, supabase_spy: FakeSupabase) -> None:
    record_service.all_records(supabase_spy)  # type: ignore[arg-type]
    assert ("eq", ("status", "completed"), {}) in supabase_spy.calls


# --- the count is remembered, and forgotten the moment a result changes ----


def test_the_count_is_remembered_between_requests(club: Any, supabase_spy: FakeSupabase) -> None:
    first = record_service.all_records(supabase_spy)  # type: ignore[arg-type]
    club["matches"].append(match("team1"))
    assert record_service.all_records(supabase_spy) is first  # type: ignore[arg-type]
    record_service.invalidate()
    assert record_service.all_records(supabase_spy)[uuid_of(AEKK)].games == 8  # type: ignore[arg-type]


def uuid_of(pid: str) -> Any:
    from uuid import UUID

    return UUID(pid)


def test_recording_a_result_shows_on_the_next_read(client: TestClient, club: Any) -> None:
    """The members list is read, a result comes in, the list is read again:
    the new game has to be on it, not a minute later."""
    assert record(next(s for s in client.get("/api/players").json() if s["player"]["id"] == AEKK))["games"] == 7

    pending = match(None, status="in_progress")
    club["matches"].insert(0, pending)  # what the result endpoint loads first
    headers = {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}
    response = client.post(f"/api/admin/matchmaking/matches/{pending['id']}/result", json={"winner": "team1"}, headers=headers)
    assert response.status_code == 200, response.text
    # The fake does not apply the update, so mark it completed the way the
    # database would have.
    pending.update(status="completed", winner="team1")

    after = record(next(s for s in client.get("/api/players").json() if s["player"]["id"] == AEKK))
    assert after == {"games": 8, "wins": 5, "draws": 3, "losses": 0}


def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def aekk_on_the_list(client: TestClient) -> dict[str, int]:
    return record(next(s for s in client.get("/api/players").json() if s["player"]["id"] == AEKK))


def test_correcting_a_result_shows_on_the_next_read(client: TestClient, club: Any) -> None:
    assert aekk_on_the_list(client) == TRUTH[AEKK]

    first = club["matches"][0]  # a team1 win, which is what PATCH loads first
    response = client.patch(f"/api/admin/matchmaking/matches/{first['id']}/result", json={"winner": "team2"}, headers=admin())
    assert response.status_code == 200, response.text
    first["winner"] = "team2"  # what the database now holds

    assert aekk_on_the_list(client) == {"games": 7, "wins": 3, "draws": 3, "losses": 1}


def test_deleting_a_night_shows_on_the_next_read(client: TestClient, club: Any) -> None:
    assert aekk_on_the_list(client) == TRUTH[AEKK]

    response = client.delete(f"/api/admin/sessions/{NIGHT}", headers=admin())
    assert response.status_code == 204, response.text
    club["matches"].clear()  # the cascade took the night's matches with it

    assert aekk_on_the_list(client) == {"games": 0, "wins": 0, "draws": 0, "losses": 0}
