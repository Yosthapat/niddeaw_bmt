from uuid import uuid4

from app.services import elo_service


def test_equal_ratings_win_gains_half_k() -> None:
    delta_winner, delta_loser = elo_service.compute_deltas([1000], [1000], "team1")
    assert delta_winner == 2
    assert delta_loser == -2


def test_draw_between_equal_ratings_is_a_no_op() -> None:
    delta1, delta2 = elo_service.compute_deltas([1000], [1000], "draw")
    assert delta1 == 0
    assert delta2 == 0


def test_underdog_win_gains_more_than_k_half() -> None:
    delta_underdog, delta_favorite = elo_service.compute_deltas([900], [1100], "team1")
    assert delta_underdog > 2
    assert delta_favorite < -2


def test_doubles_team_rating_is_average() -> None:
    assert elo_service.team_rating([1000, 1200]) == 1100


def test_score_floor_prevents_negative_rating() -> None:
    assert elo_service.apply_delta(110, -50) == 100


def test_tier_boundaries() -> None:
    assert elo_service.get_tier(899) == "milk"
    assert elo_service.get_tier(900) == "beer"
    assert elo_service.get_tier(1099) == "beer"
    assert elo_service.get_tier(1100) == "highball"
    assert elo_service.get_tier(1299) == "highball"
    assert elo_service.get_tier(1300) == "wine"
    assert elo_service.get_tier(1499) == "wine"
    assert elo_service.get_tier(1500) == "soju"
    assert elo_service.get_tier(1699) == "soju"
    assert elo_service.get_tier(1700) == "whisky"
    assert elo_service.get_tier(1899) == "whisky"
    assert elo_service.get_tier(1900) == "vodka"
    assert elo_service.get_tier(2099) == "vodka"
    assert elo_service.get_tier(2100) == "absinthe"


def test_reverse_match_results_undoes_a_single_completed_match() -> None:
    winner, loser = uuid4(), uuid4()
    players_by_id = {
        winner: {"elo_score": 1002, "games": 1, "wins": 1, "draws": 0, "losses": 0},
        loser: {"elo_score": 998, "games": 1, "wins": 0, "draws": 0, "losses": 1},
    }
    matches: list[elo_service.CompletedMatchRow] = [
        {
            "team1_player_ids": [str(winner)],
            "team2_player_ids": [str(loser)],
            "winner": "team1",
            "elo_delta_team1": 2,
            "elo_delta_team2": -2,
        }
    ]

    result = elo_service.reverse_match_results(matches, players_by_id)  # type: ignore[arg-type]

    assert result[winner] == {"elo_score": 1000, "games": 0, "wins": 0, "draws": 0, "losses": 0}
    assert result[loser] == {"elo_score": 1000, "games": 0, "wins": 0, "draws": 0, "losses": 0}


def test_reverse_match_results_skips_matches_missing_recorded_deltas() -> None:
    """Matches recorded before elo_delta_team1/2 existed have no delta to
    undo — leave the player's stats untouched rather than guessing."""
    player = uuid4()
    players_by_id = {player: {"elo_score": 1010, "games": 3, "wins": 2, "draws": 0, "losses": 1}}
    matches: list[elo_service.CompletedMatchRow] = [
        {
            "team1_player_ids": [str(player)],
            "team2_player_ids": [str(uuid4())],
            "winner": "team1",
            "elo_delta_team1": None,
            "elo_delta_team2": None,
        }
    ]

    result = elo_service.reverse_match_results(matches, players_by_id)  # type: ignore[arg-type]

    assert result[player] == players_by_id[player]


def test_reverse_match_results_never_goes_negative() -> None:
    """Defensive floor — stats shouldn't already be inconsistent, but a
    double-undo (e.g. re-running this on an already-reversed player)
    should still not produce negative counters."""
    player = uuid4()
    players_by_id = {player: {"elo_score": 100, "games": 0, "wins": 0, "draws": 0, "losses": 0}}
    matches: list[elo_service.CompletedMatchRow] = [
        {
            "team1_player_ids": [str(player)],
            "team2_player_ids": [str(uuid4())],
            "winner": "team1",
            "elo_delta_team1": 2,
            "elo_delta_team2": -2,
        }
    ]

    result = elo_service.reverse_match_results(matches, players_by_id)  # type: ignore[arg-type]

    assert result[player]["games"] == 0
    assert result[player]["wins"] == 0
