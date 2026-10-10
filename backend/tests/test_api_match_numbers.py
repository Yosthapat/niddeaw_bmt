"""The club-wide match number.

The number is a rank over every match ever played, so Postgres computes it
with a window function in the matches_numbered view (db/migrations/0025) —
PostgREST has no way to express one. That makes *which relation a read asks
for* the thing worth testing: the fake serves the same rows under either
name, so a read quietly switched back to the bare `matches` table would still
return matches, just with no number on them. These tests watch the relation.
"""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import FakeSupabase

VIEW = "matches_numbered"
S_ID = str(uuid4())
P1, P2, P3, P4 = (str(uuid4()) for _ in range(4))


def player_row(pid: str, seq: int) -> dict[str, Any]:
    return {
        "id": pid,
        "nickname": f"p{seq}",
        "line_id": None,
        "avatar_url": None,
        "elo_score": 1000 + seq,
        "elo_level": "milk",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
        "member_seq": seq,
        "games": 4,
        "wins": 2,
        "draws": 0,
        "losses": 2,
    }


PLAYER_ROWS = [player_row(pid, i + 1) for i, pid in enumerate((P1, P2, P3, P4))]


def match_row(no: int, match_id: str | None = None) -> dict[str, Any]:
    return {
        "id": match_id or str(uuid4()),
        "session_id": S_ID,
        "type": "double",
        "team1_player_ids": [P1, P2],
        "team2_player_ids": [P3, P4],
        "sets": None,
        "winner": "team1",
        "status": "completed",
        "court": "1",
        "elo_delta_team1": 8,
        "elo_delta_team2": -8,
        "created_at": "2026-10-09T13:00:00Z",
        "updated_at": "2026-10-09T13:20:00Z",
        "match_no": no,
    }


def test_the_match_log_reads_the_numbered_view(
    client: TestClient,
    supabase_rows: dict[str, list[dict[str, Any]]],
    supabase_spy: FakeSupabase,
) -> None:
    supabase_rows[VIEW] = [match_row(12), match_row(11)]
    response = client.get("/api/matches")
    assert response.status_code == 200
    assert VIEW in supabase_spy.requested
    assert [m["match_no"] for m in response.json()] == [12, 11]


def test_the_match_log_carries_the_number_through_untouched(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The API must not renumber per page: the number belongs to the match,
    not to its position in whatever slice was asked for."""
    supabase_rows[VIEW] = [match_row(900), match_row(899), match_row(898)]
    body = client.get("/api/matches?limit=3&offset=50").json()
    assert [m["match_no"] for m in body] == [900, 899, 898]


def test_a_single_match_page_reads_the_numbered_view(
    client: TestClient,
    supabase_rows: dict[str, list[dict[str, Any]]],
    supabase_spy: FakeSupabase,
) -> None:
    mid = str(uuid4())
    supabase_rows[VIEW] = [match_row(7, mid)]
    supabase_rows["players"] = PLAYER_ROWS
    response = client.get(f"/api/matches/{mid}/detail")
    assert response.status_code == 200
    assert VIEW in supabase_spy.requested
    assert response.json()["match"]["match_no"] == 7


def test_a_match_with_no_number_is_still_served(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """match_no is optional on the model so a row that came back from a write
    — which reads the table, not the view — does not blow up validation."""
    row = match_row(3)
    del row["match_no"]
    supabase_rows[VIEW] = [row]
    body = client.get("/api/matches").json()
    assert body[0]["match_no"] is None


def test_the_count_endpoint_still_reads_the_table(
    client: TestClient,
    supabase_rows: dict[str, list[dict[str, Any]]],
    supabase_spy: FakeSupabase,
) -> None:
    """Counting needs no rank, and the view would make Postgres number every
    match in the club's history just to throw the numbers away."""
    supabase_rows["matches"] = [match_row(1)]
    assert client.get("/api/matches/count").status_code == 200
    assert "matches" in supabase_spy.requested
