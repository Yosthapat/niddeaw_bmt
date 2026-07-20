"""Pure ELO rating math — no I/O, fully unit-testable.

K-factor is flat (no provisional-K ramp) — kept simple for a casual club.
Doubles teams are rated by the average of their two players' scores, and
the resulting delta is applied identically to both teammates.
"""

from app.models.player import EloTier

K_FACTOR = 32
STARTING_SCORE = 1000
SCORE_FLOOR = 100

_TIER_THRESHOLDS: list[tuple[int, EloTier]] = [
    (900, "milk"),
    (1100, "soju"),
    (1250, "beer"),
    (1400, "whisky"),
    (1550, "highball"),
]


def get_tier(score: int) -> EloTier:
    for threshold, tier in _TIER_THRESHOLDS:
        if score < threshold:
            return tier
    return "vodka"


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def team_rating(player_scores: list[int]) -> float:
    return sum(player_scores) / len(player_scores)


def compute_deltas(
    team1_scores: list[int], team2_scores: list[int], winner: str
) -> tuple[int, int]:
    """Return (delta_for_team1_players, delta_for_team2_players).

    winner: "team1" | "team2" | "draw"
    """
    team1_avg = team_rating(team1_scores)
    team2_avg = team_rating(team2_scores)

    expected1 = expected_score(team1_avg, team2_avg)
    expected2 = 1 - expected1

    if winner == "team1":
        actual1 = 1.0
    elif winner == "team2":
        actual1 = 0.0
    else:
        actual1 = 0.5
    actual2 = 1 - actual1

    delta1 = round(K_FACTOR * (actual1 - expected1))
    delta2 = round(K_FACTOR * (actual2 - expected2))
    return delta1, delta2


def apply_delta(current_score: int, delta: int) -> int:
    return max(SCORE_FLOOR, current_score + delta)
