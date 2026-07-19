from datetime import datetime, timedelta

from app.services import billing_service


def _times(minutes: int) -> tuple[datetime, datetime]:
    start = datetime(2026, 1, 1, 18, 0, 0)
    return start, start + timedelta(minutes=minutes)


def test_exact_hour_bills_one_hour() -> None:
    checkin, checkout = _times(60)
    assert billing_service.compute_hours_played(checkin, checkout) == 1.0


def test_grace_period_does_not_bump_next_block() -> None:
    checkin, checkout = _times(64)  # 4 min over, within 5-min grace
    assert billing_service.compute_hours_played(checkin, checkout) == 1.0


def test_beyond_grace_period_rounds_up_to_next_block() -> None:
    checkin, checkout = _times(66)  # 6 min over grace -> bump to next 30-min block
    assert billing_service.compute_hours_played(checkin, checkout) == 1.5


def test_amount_calc_uses_rate_per_hour() -> None:
    assert billing_service.compute_amount_calc(1.5, 50.0) == 75.0


def test_effective_amount_prefers_adjustment() -> None:
    assert billing_service.effective_amount(100.0, 80.0) == 80.0
    assert billing_service.effective_amount(100.0, None) == 100.0
