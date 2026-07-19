from app.services import billing_service


def test_court_fee_only_when_no_games_played() -> None:
    assert billing_service.compute_amount_calc(0, 80.0, 29.0) == 80.0


def test_adds_flat_shuttlecock_cost_per_game_not_split() -> None:
    assert billing_service.compute_amount_calc(3, 80.0, 29.0) == 80.0 + 3 * 29.0


def test_effective_amount_prefers_adjustment() -> None:
    assert billing_service.effective_amount(100.0, 80.0) == 80.0
    assert billing_service.effective_amount(100.0, None) == 100.0
