"""Guards against two mistakes a tired admin makes on a club night.

Both were found by driving the real UI against the real app: the browser's
Back button returns to the result screen with its buttons live, and the
session picker lists closed sessions, so the next tap lands on the wrong
night. Neither is reachable from the service layer, so neither could have
been caught by the service tests — these go through the HTTP API.
"""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.security import create_access_token

SESSION_ID = str(uuid4())
MATCH_ID = str(uuid4())
PLAYER_IDS = [str(uuid4()) for _ in range(4)]


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def session_row(status: str) -> dict[str, Any]:
    return {
        "id": SESSION_ID, "date": "2026-10-09", "location": "คอร์ตนิดเดียว",
        "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
        "status": status, "created_by": str(uuid4()), "created_at": "2026-10-09T12:00:00Z",
    }


def match_row(status: str) -> dict[str, Any]:
    return {
        "id": MATCH_ID, "session_id": SESSION_ID, "type": "double",
        "team1_player_ids": PLAYER_IDS[:2], "team2_player_ids": PLAYER_IDS[2:],
        "sets": None, "winner": None, "status": status, "court": "1",
        "elo_delta_team1": None, "elo_delta_team2": None,
        "created_at": "2026-10-09T13:00:00Z", "updated_at": "2026-10-09T13:00:00Z",
    }


def player_rows() -> list[dict[str, Any]]:
    return [
        {"id": pid, "elo_score": 1000, "games": 0, "wins": 0, "draws": 0, "losses": 0}
        for pid in PLAYER_IDS
    ]


def confirm_payload() -> dict[str, Any]:
    return {
        "session_id": SESSION_ID, "type": "double",
        "team1_player_ids": PLAYER_IDS[:2], "team2_player_ids": PLAYER_IDS[2:],
        "status": "queued",
    }


def test_check_in_is_refused_once_the_session_is_closed(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Closing is what bills everyone, so a later check-in is a player with
    no bill."""
    supabase_rows["sessions"] = [session_row("closed")]
    response = client.post(
        "/api/admin/checkins",
        json={"session_id": SESSION_ID, "player_id": PLAYER_IDS[0]},
        headers=auth(),
    )
    assert response.status_code == 409


def test_check_in_still_works_while_the_session_is_open(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["checkins"] = [
        {"id": str(uuid4()), "session_id": SESSION_ID, "player_id": PLAYER_IDS[0],
         "checkin_time": "2026-10-09T13:00:00Z", "checkout_time": None}
    ]
    response = client.post(
        "/api/admin/checkins",
        json={"session_id": SESSION_ID, "player_id": PLAYER_IDS[0]},
        headers=auth(),
    )
    assert response.status_code == 201


def test_check_in_on_a_session_that_does_not_exist_is_a_404(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = []
    response = client.post(
        "/api/admin/checkins",
        json={"session_id": SESSION_ID, "player_id": PLAYER_IDS[0]},
        headers=auth(),
    )
    assert response.status_code == 404


def test_a_match_cannot_be_created_in_a_closed_session(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("closed")]
    response = client.post(
        "/api/admin/matchmaking/confirm", json=confirm_payload(), headers=auth()
    )
    assert response.status_code == 409


def test_a_match_can_still_be_created_while_the_session_is_open(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    # The row the insert hands back. Its players are four other people: the
    # fake serves this same row to the "is anyone already paired?" read, so
    # reusing our four would look like a clash and mask the thing under test.
    others = [str(uuid4()) for _ in range(4)]
    supabase_rows["matches"] = [
        dict(match_row("queued"), team1_player_ids=others[:2], team2_player_ids=others[2:])
    ]
    response = client.post(
        "/api/admin/matchmaking/confirm", json=confirm_payload(), headers=auth()
    )
    assert response.status_code == 201


def test_a_result_cannot_be_recorded_twice(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The second POST is what the browser's Back button sends. Without the
    guard it applies ELO again and gives everyone a second game played."""
    supabase_rows["matches"] = [match_row("completed")]
    supabase_rows["players"] = player_rows()
    response = client.post(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team1"},
        headers=auth(),
    )
    assert response.status_code == 409


def test_a_result_is_still_accepted_the_first_time(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["matches"] = [match_row("in_progress")]
    supabase_rows["players"] = player_rows()
    response = client.post(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team1"},
        headers=auth(),
    )
    assert response.status_code == 200


# --- fixing a result that was recorded for the wrong team ---------------


def completed_match(**overrides: Any) -> dict[str, Any]:
    row = dict(
        match_row("completed"),
        winner="team1",
        elo_delta_team1=2,
        elo_delta_team2=-2,
    )
    row.update(overrides)
    return row


def test_a_wrong_result_can_be_corrected(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [completed_match()]
    supabase_rows["players"] = player_rows()
    response = client.patch(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team2"},
        headers=auth(),
    )
    assert response.status_code == 200


def test_correcting_to_the_same_winner_changes_nothing(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """No players are even read: re-sending the result already recorded must
    not reverse and re-apply the same deltas for nothing."""
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [completed_match()]
    supabase_rows["players"] = player_rows()
    response = client.patch(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team1"},
        headers=auth(),
    )
    assert response.status_code == 200
    assert response.json()["winner"] == "team1"


def test_a_result_cannot_be_corrected_once_the_session_is_closed(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Closed means billed, and the bills were raised from these matches."""
    supabase_rows["sessions"] = [session_row("closed")]
    supabase_rows["matches"] = [completed_match()]
    supabase_rows["players"] = player_rows()
    response = client.patch(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team2"},
        headers=auth(),
    )
    assert response.status_code == 409


def test_a_match_recorded_before_elo_deltas_existed_cannot_be_corrected(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Without the stored deltas there is nothing to reverse by, and a guess
    would skew the ladder silently."""
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [completed_match(elo_delta_team1=None, elo_delta_team2=None)]
    supabase_rows["players"] = player_rows()
    response = client.patch(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team2"},
        headers=auth(),
    )
    assert response.status_code == 409


def test_a_match_with_no_result_yet_is_not_corrected_but_recorded(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [match_row("in_progress")]
    supabase_rows["players"] = player_rows()
    response = client.patch(
        f"/api/admin/matchmaking/matches/{MATCH_ID}/result",
        json={"winner": "team2"},
        headers=auth(),
    )
    assert response.status_code == 409


# --- billing one player checks them out ---------------------------------


def billing_row() -> dict[str, Any]:
    return {
        "id": str(uuid4()), "session_id": SESSION_ID, "player_id": PLAYER_IDS[0],
        "game_count": 1, "amount_calc": 109.0, "amount_adjusted": None,
        "paid_status": "unpaid", "promptpay_ref": None,
        "updated_at": "2026-10-09T15:00:00Z",
    }


def test_billing_a_player_checks_them_out(
    client: TestClient, supabase_spy: Any, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    # Four other people's match: the fake ignores the status filter, so a
    # match holding this player would read as one they are still in and the
    # billing would be refused for the wrong reason.
    others = [str(uuid4()) for _ in range(4)]
    supabase_rows["matches"] = [
        completed_match(team1_player_ids=others[:2], team2_player_ids=others[2:])
    ]
    supabase_rows["billings"] = [billing_row()]
    response = client.post(
        f"/api/admin/billing/player/{SESSION_ID}/{PLAYER_IDS[0]}", headers=auth()
    )
    assert response.status_code == 200
    # the checkout is part of billing now, not a second button
    assert "checkins" in supabase_spy.requested


def test_a_player_with_a_match_still_on_court_cannot_be_billed(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Their bill counts completed games, so billing now would miss the one
    they are in the middle of and the club would be short."""
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [match_row("in_progress")]
    response = client.post(
        f"/api/admin/billing/player/{SESSION_ID}/{PLAYER_IDS[0]}", headers=auth()
    )
    assert response.status_code == 409


def test_a_player_with_a_match_still_queued_cannot_be_billed(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [session_row("open")]
    supabase_rows["matches"] = [match_row("queued")]
    response = client.post(
        f"/api/admin/billing/player/{SESSION_ID}/{PLAYER_IDS[0]}", headers=auth()
    )
    assert response.status_code == 409
