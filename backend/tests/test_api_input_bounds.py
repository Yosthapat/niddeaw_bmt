"""What the admin forms can no longer store.

Each of these went straight into the database before, found by posting
them at the running API: a blank location, a negative court fee (which
bills the whole club a credit), a fee with a typo's worth of zeros, a
negative expense, an ELO of 999999, and a PromptPay id of "abc" — which
becomes a QR the banking app rejects at the till. Refused before any row
is touched, so the fake database is never even consulted.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.security import create_access_token
from app.services.promptpay_service import id_problem


@pytest.fixture(autouse=True)
def _fake_db(supabase_rows: dict[str, list[dict[str, Any]]]) -> None:
    """Every request gets the fake, so a refusal that came from the
    database (rather than from the bounds) would show up as a pass."""


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def session(**overrides: Any) -> dict[str, Any]:
    body = {
        "date": "2026-10-30",
        "location": "KB badminton court โยธินพัฒนา",
        "court_fee_per_person": 80,
        "shuttlecock_price_per_game": 29,
    }
    return {**body, **overrides}


@pytest.mark.parametrize(
    "overrides",
    [
        {"location": "   "},
        {"location": "x" * 121},
        {"court_fee_per_person": -80},
        {"shuttlecock_price_per_game": -1},
        {"court_fee_per_person": 1e12},
    ],
)
def test_a_session_with_an_impossible_value_is_refused(
    client: TestClient, overrides: dict[str, Any]
) -> None:
    response = client.post("/api/admin/sessions", json=session(**overrides), headers=auth())
    assert response.status_code == 422


def test_a_free_night_is_still_a_night(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Zero is a real fee — a sponsored night, a donated tube."""
    supabase_rows["sessions"] = [
        {
            **session(court_fee_per_person=0, shuttlecock_price_per_game=0),
            "id": str(uuid4()), "status": "open", "created_by": str(uuid4()),
            "created_at": "2026-10-30T12:00:00Z",
        }
    ]
    response = client.post(
        "/api/admin/sessions",
        json=session(court_fee_per_person=0, shuttlecock_price_per_game=0),
        headers=auth(),
    )
    assert response.status_code == 201


def test_a_location_is_stored_without_its_stray_spaces(
    client: TestClient, supabase_spy: Any
) -> None:
    supabase_spy.tables["sessions"] = [
        {
            **session(), "id": str(uuid4()), "status": "open",
            "created_by": str(uuid4()), "created_at": "2026-10-30T12:00:00Z",
        }
    ]
    client.post("/api/admin/sessions", json=session(location="  Guy court  "), headers=auth())
    inserts = [args for name, args, _ in supabase_spy.calls if name == "insert"]
    assert inserts and inserts[0][0]["location"] == "Guy court"


def test_a_bill_cannot_be_adjusted_below_zero(client: TestClient) -> None:
    response = client.patch(
        f"/api/admin/billing/{uuid4()}/adjust", json={"amount_adjusted": -500}, headers=auth()
    )
    assert response.status_code == 422


@pytest.mark.parametrize("amount", [0, -10])
def test_an_expense_has_to_cost_something(client: TestClient, amount: float) -> None:
    response = client.post(
        "/api/admin/expenses",
        json={
            "expense_date": "2026-10-27", "category": "shuttlecock",
            "amount": amount, "paid_by": str(uuid4()),
        },
        headers=auth(),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides", [{"amount": -1}, {"source_name": "  "}, {"note": "x" * 501}]
)
def test_income_needs_a_name_and_an_amount(
    client: TestClient, overrides: dict[str, Any]
) -> None:
    body = {"income_date": "2026-10-27", "source": "sponsor", "source_name": "Wasteland", "amount": 500}
    response = client.post("/api/admin/income", json={**body, **overrides}, headers=auth())
    assert response.status_code == 422


@pytest.mark.parametrize(
    "body", [{"nickname": "Zed", "elo_score": 999999}, {"nickname": "Zed", "line_id": "y" * 101}]
)
def test_a_member_cannot_be_created_with_a_typo_for_a_rating(
    client: TestClient, body: dict[str, Any]
) -> None:
    response = client.post("/api/admin/players", json=body, headers=auth())
    assert response.status_code == 422


def test_settings_refuse_a_promptpay_id_no_bank_could_pay(client: TestClient) -> None:
    response = client.put(
        "/api/admin/settings",
        json={"payment_method": "promptpay", "promptpay_id": "abc", "promptpay_type": "phone"},
        headers=auth(),
    )
    assert response.status_code == 400
    assert "10 หลัก" in response.json()["detail"]


@pytest.mark.parametrize(
    ("promptpay_id", "kind", "method", "ok"),
    [
        ("0812345678", "phone", "promptpay", True),
        ("081-234-5678", "phone", "promptpay", True),
        ("081234567", "phone", "promptpay", False),
        ("8123456789", "phone", "promptpay", False),
        ("1234567890123", "national_id", "promptpay", True),
        ("123456789012", "national_id", "promptpay", False),
        ("123456789012345", "ewallet", "promptpay", True),
        ("", "phone", "promptpay", False),
        ("", "phone", "bank_account", True),
        ("abc", "phone", "bank_account", False),
    ],
)
def test_which_promptpay_ids_make_a_payable_qr(
    promptpay_id: str, kind: str, method: str, ok: bool
) -> None:
    assert (id_problem(promptpay_id, kind, method) is None) is ok
