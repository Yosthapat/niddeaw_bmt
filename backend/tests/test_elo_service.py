from app.services import elo_service


def test_equal_ratings_win_gains_half_k() -> None:
    delta_winner, delta_loser = elo_service.compute_deltas([1000], [1000], "team1")
    assert delta_winner == 16
    assert delta_loser == -16


def test_draw_between_equal_ratings_is_a_no_op() -> None:
    delta1, delta2 = elo_service.compute_deltas([1000], [1000], "draw")
    assert delta1 == 0
    assert delta2 == 0


def test_underdog_win_gains_more_than_k_half() -> None:
    delta_underdog, delta_favorite = elo_service.compute_deltas([900], [1100], "team1")
    assert delta_underdog > 16
    assert delta_favorite < -16


def test_doubles_team_rating_is_average() -> None:
    assert elo_service.team_rating([1000, 1200]) == 1100


def test_score_floor_prevents_negative_rating() -> None:
    assert elo_service.apply_delta(110, -50) == 100


def test_tier_boundaries() -> None:
    assert elo_service.get_tier(899) == "milk"
    assert elo_service.get_tier(900) == "soju"
    assert elo_service.get_tier(1099) == "soju"
    assert elo_service.get_tier(1100) == "beer"
    assert elo_service.get_tier(1249) == "beer"
    assert elo_service.get_tier(1250) == "whisky"
    assert elo_service.get_tier(1399) == "whisky"
    assert elo_service.get_tier(1400) == "highball"
    assert elo_service.get_tier(1549) == "highball"
    assert elo_service.get_tier(1550) == "vodka"
