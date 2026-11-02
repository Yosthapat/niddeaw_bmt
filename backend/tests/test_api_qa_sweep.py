"""Requests that ended in a 500 when a validation fuzzer threw them at
every admin endpoint, and the ones the database refuses that the fakes
used in tests never would.

- An edit's `null` for a column that can't be empty (a night's location,
  a product's sizes) reached the database or the response model and
  crashed. It is now a 422 naming the field.
- A member checked out and tapped "check in" again hit the night's one
  check-in per member and crashed. It now re-opens that check-in.
- Whatever else Postgres refuses — a unique key, a row deleted a moment
  ago — is answered as a 4xx with a reason, not a bare 500.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.deps import get_supabase
from app.main import app
from app.security import create_access_token
from tests.conftest import FakeQuery, FakeResult, FakeSupabase

SESSION_ID = str(uuid4())
PLAYER_ID = str(uuid4())
ROW_ID = str(uuid4())


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


@pytest.mark.parametrize(
    ("method", "path", "field"),
    [
        ("PATCH", f"/api/admin/sessions/{ROW_ID}", "location"),
        ("PATCH", f"/api/admin/sessions/{ROW_ID}", "status"),
        ("PATCH", f"/api/admin/sessions/{ROW_ID}", "court_fee_per_person"),
        ("PATCH", f"/api/admin/players/{ROW_ID}", "nickname"),
        ("PATCH", f"/api/admin/players/{ROW_ID}", "elo_score"),
        ("PATCH", f"/api/admin/players/{ROW_ID}", "is_active"),
        ("PUT", "/api/admin/settings", "promptpay_type"),
        ("PUT", "/api/admin/settings", "payment_method"),
        ("PATCH", f"/api/admin/expenses/{ROW_ID}", "amount"),
        ("PATCH", f"/api/admin/expenses/{ROW_ID}", "category"),
        ("PATCH", f"/api/admin/income/{ROW_ID}", "source_name"),
        ("PATCH", f"/api/admin/sponsors/{ROW_ID}", "name"),
        ("PATCH", f"/api/admin/sponsors/{ROW_ID}", "is_visible"),
        ("PATCH", f"/api/admin/shop/products/{ROW_ID}", "sizes"),
        ("PATCH", f"/api/admin/shop/products/{ROW_ID}", "sale_type"),
        ("PATCH", f"/api/admin/shop/products/{ROW_ID}", "size_prices"),
    ],
)
def test_a_null_for_a_required_column_is_a_422(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]], method: str, path: str, field: str
) -> None:
    response = client.request(method, path, json={field: None}, headers=auth())
    assert response.status_code == 422, response.text
    assert field in response.text


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", f"/api/admin/players/{ROW_ID}", {"avatar_url": None, "line_id": None, "quote": None}),
        ("PATCH", f"/api/admin/expenses/{ROW_ID}", {"note": None, "category_other": None}),
        ("PATCH", f"/api/admin/sponsors/{ROW_ID}", {"href": None}),
        ("PUT", "/api/admin/settings", {"bank_name": None}),
    ],
)
def test_a_null_still_clears_a_column_that_may_be_empty(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]], method: str, path: str, body: dict[str, Any]
) -> None:
    """Clearing a member's LINE id or a sponsor's link is what null is for."""
    response = client.request(method, path, json=body, headers=auth())
    assert response.status_code != 422, response.text


def open_session() -> dict[str, Any]:
    return {
        "id": SESSION_ID, "date": "2026-10-09", "location": "คอร์ตนิดเดียว",
        "court_fee_per_person": 80, "shuttlecock_price_per_game": 29,
        "status": "open", "created_by": str(uuid4()), "created_at": "2026-10-09T12:00:00Z",
    }


def checkin(checkout_time: str | None) -> dict[str, Any]:
    return {
        "id": ROW_ID, "session_id": SESSION_ID, "player_id": PLAYER_ID,
        "checkin_time": "2026-10-09T13:00:00Z", "checkout_time": checkout_time,
    }


def test_checking_a_checked_out_member_back_in_reopens_their_check_in(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]], supabase_spy: FakeSupabase
) -> None:
    supabase_rows["sessions"] = [open_session()]
    supabase_rows["players"] = [{"id": PLAYER_ID}]
    supabase_rows["checkins"] = [checkin("2026-10-09T14:00:00Z")]
    response = client.post("/api/admin/checkins", json={"session_id": SESSION_ID, "player_id": PLAYER_ID}, headers=auth())
    assert response.status_code == 201, response.text
    assert ("update", ({"checkout_time": None},), {}) in supabase_spy.calls
    assert not [c for c in supabase_spy.calls if c[0] == "insert"]


def test_checking_in_someone_already_in_gives_back_their_check_in(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]], supabase_spy: FakeSupabase
) -> None:
    """A double tap at the door, or two admins at once."""
    supabase_rows["sessions"] = [open_session()]
    supabase_rows["players"] = [{"id": PLAYER_ID}]
    supabase_rows["checkins"] = [checkin(None)]
    response = client.post("/api/admin/checkins", json={"session_id": SESSION_ID, "player_id": PLAYER_ID}, headers=auth())
    assert response.status_code == 201
    assert response.json()["id"] == ROW_ID
    assert not [c for c in supabase_spy.calls if c[0] in ("insert", "update")]


def test_checking_in_a_member_who_does_not_exist_is_a_404(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["sessions"] = [open_session()]
    supabase_rows["players"] = []
    response = client.post("/api/admin/checkins", json={"session_id": SESSION_ID, "player_id": PLAYER_ID}, headers=auth())
    assert response.status_code == 404


class RefusingQuery(FakeQuery):
    def __init__(self, code: str) -> None:
        super().__init__([])
        self._code = code

    def execute(self) -> FakeResult:
        raise APIError({"code": self._code, "message": "refused", "details": "secret detail", "hint": None})


class RefusingSupabase(FakeSupabase):
    def __init__(self, code: str) -> None:
        super().__init__()
        self._code = code

    def table(self, name: str) -> FakeQuery:
        return RefusingQuery(self._code)


@pytest.mark.parametrize(
    ("code", "status"),
    [("23505", 409), ("23503", 409), ("23502", 400), ("23514", 400), ("22P02", 400)],
)
def test_a_write_the_database_refuses_is_a_4xx_with_a_reason(client: TestClient, code: str, status: int) -> None:
    app.dependency_overrides[get_supabase] = lambda: RefusingSupabase(code)
    try:
        response = client.post(
            "/api/admin/sessions",
            json={"date": "2026-11-06", "location": "x", "court_fee_per_person": 1, "shuttlecock_price_per_game": 1},
            headers=auth(),
        )
    finally:
        app.dependency_overrides.pop(get_supabase, None)
    assert response.status_code == status
    assert "secret detail" not in response.text
    assert response.json()["detail"]


def test_any_other_database_error_is_still_a_500() -> None:
    app.dependency_overrides[get_supabase] = lambda: RefusingSupabase("42501")
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            response = c.get("/api/admin/sessions", headers=auth())
    finally:
        app.dependency_overrides.pop(get_supabase, None)
    assert response.status_code == 500


def test_money_is_kept_to_the_satang() -> None:
    """numeric(10, 2) keeps two places: 0.004 would be stored as 0.00 and
    then refused by `amount > 0`, so it is refused here, with a reason."""
    from pydantic import TypeAdapter, ValidationError

    from app.models.fields import Baht, PositiveBaht

    positive: TypeAdapter[float] = TypeAdapter(PositiveBaht)
    assert positive.validate_python(1.006) == 1.01
    assert positive.validate_python(0.01) == 0.01
    for nothing in (0.004, 0.0049):
        with pytest.raises(ValidationError):
            positive.validate_python(nothing)
    assert TypeAdapter(Baht).validate_python(0.004) == 0.0


def test_an_expense_of_less_than_a_satang_is_a_422(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    response = client.post(
        "/api/admin/expenses",
        json={"expense_date": "2026-11-06", "category": "court_fee", "amount": 0.004, "paid_by": str(uuid4())},
        headers=auth(),
    )
    assert response.status_code == 422
