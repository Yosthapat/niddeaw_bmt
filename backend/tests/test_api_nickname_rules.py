"""Adding and renaming a member, through the API that both screens call.

The admin screen and the check-in screen each have their own add form, so
the rules have to hold here rather than in either of them.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services import nickname_service
from tests.conftest import FakeSupabase

EXISTING_ID = "11111111-1111-1111-1111-111111111111"


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token()}"}


def create_token() -> str:
    from app.security import create_access_token

    return create_access_token(admin_id=str(uuid4()), role="admin")


def player(player_id: str, nickname: str, *, active: bool = True) -> dict[str, Any]:
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


def add(client: TestClient, nickname: str) -> Any:
    return client.post("/api/admin/players", json={"nickname": nickname}, headers=auth())


def rename(client: TestClient, player_id: str, nickname: str) -> Any:
    return client.patch(
        f"/api/admin/players/{player_id}", json={"nickname": nickname}, headers=auth()
    )


# --- the format rules, as the API answers them ---------------------------


def test_a_good_name_is_accepted(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [player(EXISTING_ID, "Ball")]
    assert add(client, "Shane").status_code == 201


def test_a_thai_name_is_refused_with_a_reason(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = []
    response = add(client, "บอล")
    assert response.status_code == 400
    assert response.json()["detail"] == nickname_service.NOT_ENGLISH


def test_a_lowercase_name_is_refused_with_a_reason(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = []
    response = add(client, "shane")
    assert response.status_code == 400
    assert response.json()["detail"] == nickname_service.NOT_CAPITALISED


def test_the_name_is_stored_tidied_up(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [player(EXISTING_ID, "Someone Else")]
    add(client, "  Big   Boy ")
    inserted = [c for c in supabase_spy.calls if c[0] == "insert"]
    assert inserted and inserted[0][1][0]["nickname"] == "Big Boy"


# --- the duplicate rule --------------------------------------------------


def test_the_same_name_is_refused(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [player(EXISTING_ID, "Ball")]
    response = add(client, "Ball")
    assert response.status_code == 409
    assert "Ball" in response.json()["detail"]


def test_a_deleted_members_name_is_free_again(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Someone who has left the club does not retire their nickname.

    The fake applies no filter but ilike, so what proves this is that the
    request asked for active members only.
    """
    supabase_rows["players"] = [player(EXISTING_ID, "Ball", active=False)]
    add(client, "Ball")
    assert ("eq", ("is_active", True), {}) in supabase_spy.calls


def test_the_check_ignores_capitals(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The fake matches nothing itself, so what proves this is that the
    request asked for a case-insensitive match on the whole name."""
    supabase_rows["players"] = [player(EXISTING_ID, "Ball")]
    add(client, "BALL")
    assert ("ilike", ("nickname", "BALL"), {}) in supabase_spy.calls


def test_a_name_that_only_looks_similar_is_free(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """"Balll" is a real member here, and "Ball" has to stay available."""
    supabase_rows["players"] = [player(EXISTING_ID, "Balll")]
    assert add(client, "Ball").status_code == 201


# --- renaming ------------------------------------------------------------


def test_renaming_keeps_the_rules(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [player(EXISTING_ID, "Ball")]
    assert rename(client, EXISTING_ID, "ball").status_code == 400
    assert rename(client, EXISTING_ID, "บอล").status_code == 400


def test_a_member_does_not_clash_with_their_own_name(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Saving the edit form without touching the name must not 409."""
    supabase_rows["players"] = [player(EXISTING_ID, "Ball")]
    assert rename(client, EXISTING_ID, "Ball").status_code == 200


def test_changing_something_else_does_not_run_the_name_rules(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """A member whose name predates the rules can still have their ELO or
    their Instagram edited."""
    supabase_rows["players"] = [player(EXISTING_ID, "oldname")]
    response = client.patch(
        f"/api/admin/players/{EXISTING_ID}", json={"instagram": "x"}, headers=auth()
    )
    assert response.status_code == 200


def test_deactivating_a_member_does_not_run_the_name_rules(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = [player(EXISTING_ID, "oldname")]
    response = client.patch(
        f"/api/admin/players/{EXISTING_ID}", json={"is_active": False}, headers=auth()
    )
    assert response.status_code == 200


# --- who the rules are for -----------------------------------------------


def test_adding_a_member_still_needs_an_admin(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = []
    assert client.post("/api/admin/players", json={"nickname": "Shane"}).status_code == 401
