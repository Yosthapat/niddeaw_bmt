from datetime import date

from app.services import revenue_service

SESSIONS = [
    {"id": "s1", "date": "2026-07-19"},
    {"id": "s2", "date": "2026-07-19"},
    {"id": "s3", "date": "2026-07-20"},
]


def test_groups_by_session_date_not_billing_row() -> None:
    billings = [
        {"session_id": "s1", "amount_calc": 109.0, "amount_adjusted": None, "paid_status": "paid"},
        {"session_id": "s2", "amount_calc": 109.0, "amount_adjusted": None, "paid_status": "unpaid"},
        {"session_id": "s3", "amount_calc": 80.0, "amount_adjusted": None, "paid_status": "paid"},
    ]
    daily = revenue_service.build_daily_revenue(SESSIONS, billings)  # type: ignore[arg-type]

    assert [d.date for d in daily] == [date(2026, 7, 20), date(2026, 7, 19)]

    july20 = daily[0]
    assert july20.total_amount == 80.0
    assert july20.session_count == 1
    assert july20.billing_count == 1

    july19 = daily[1]
    assert july19.total_amount == 218.0
    assert july19.paid_amount == 109.0
    assert july19.unpaid_amount == 109.0
    assert july19.session_count == 2
    assert july19.billing_count == 2


def test_prefers_amount_adjusted_over_amount_calc() -> None:
    billings = [
        {"session_id": "s1", "amount_calc": 109.0, "amount_adjusted": 90.0, "paid_status": "paid"},
    ]
    daily = revenue_service.build_daily_revenue(SESSIONS, billings)  # type: ignore[arg-type]
    assert daily[0].total_amount == 90.0
    assert daily[0].paid_amount == 90.0


def test_ignores_billing_with_unknown_session() -> None:
    billings = [
        {"session_id": "missing", "amount_calc": 500.0, "amount_adjusted": None, "paid_status": "paid"},
    ]
    assert revenue_service.build_daily_revenue(SESSIONS, billings) == []  # type: ignore[arg-type]


def test_no_billings_returns_empty() -> None:
    assert revenue_service.build_daily_revenue(SESSIONS, []) == []  # type: ignore[arg-type]
