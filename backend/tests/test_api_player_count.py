"""The club's member tally, as the home page reads it.

It sits beside the photo strip of the same roster, so the number and the
faces have to be counting the same people.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import FakeSupabase


def member(player_id: str, nickname: str, *, active: bool = True) -> dict[str, Any]:
    return {
        "id": player_id,
        "nickname": nickname,
        "member_seq": 1,
        "avatar_url": None,
        "elo_score": 1200,
        "elo_level": "highball",
        "is_active": active,
        "line_id": None,
        "dominant_hand": None,
        "tiktok": None,
        "instagram": None,
        "quote": None,
        "created_at": "2026-10-01T10:00:00+00:00",
    }


def test_anyone_can_read_it(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The home page is public, so this cannot need a login."""
    supabase_rows["players"] = [member("1", "กิ๊ก")]
    assert client.get("/api/players/count").status_code == 200


def test_it_reports_what_the_database_counted(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [member(str(i), f"p{i}") for i in range(7)]
    assert client.get("/api/players/count").json() == {"active": 7}


def test_an_empty_club_is_zero_not_an_error(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = []
    assert client.get("/api/players/count").json() == {"active": 0}


def test_it_asks_the_database_to_count_rather_than_fetching_the_roster(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The point of the endpoint: it must stay flat as the club grows."""
    supabase_rows["players"] = [member(str(i), f"p{i}") for i in range(3)]
    client.get("/api/players/count")
    assert supabase_spy.requested == ["players"]


def test_count_is_not_swallowed_by_the_player_id_route(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """"/count" also matches "/{player_id}"; the literal one is declared
    first so it wins. Reaching the other route would 422 on the UUID."""
    supabase_rows["players"] = [member("1", "กิ๊ก")]
    response = client.get("/api/players/count")
    assert response.status_code == 200
    assert "active" in response.json()


def test_it_counts_only_the_active_roster(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Someone deactivated has left the club.

    The fake applies no filters, so the number alone cannot show this —
    the request itself has to be read back.
    """
    supabase_rows["players"] = [member("1", "กิ๊ก"), member("2", "ต้น", active=False)]
    client.get("/api/players/count")
    assert ("eq", ("is_active", True), {}) in supabase_spy.calls
