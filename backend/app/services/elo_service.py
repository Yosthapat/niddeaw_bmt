"""Pure ELO rating math — no I/O, fully unit-testable.

K-factor is flat (no provisional-K ramp) — kept simple for a casual club.
Doubles teams are rated by the average of their two players' scores, and
the resulting delta is applied identically to both teammates.
"""

from typing import TypedDict
from uuid import UUID

from app.models.player import EloTier

K_FACTOR = 4
"""Low on purpose: an even match nets a ~2-point swing per game (not the
32-point swings of a competitive-ELO K-factor), so climbing the six tiers
is a gradual, many-games club journey rather than a fast few-game jump."""
STARTING_SCORE = 1000
SCORE_FLOOR = 100

_TIER_THRESHOLDS: list[tuple[int, EloTier]] = [
    (900, "milk"),
    (1100, "beer"),
    (1300, "highball"),
    (1500, "wine"),
    (1700, "soju"),
    (1900, "whisky"),
    (2100, "vodka"),
]
"""Ordered by rising alcohol content (Milk 0% -> Beer ~5% -> Highball ~7-9%
-> Wine ~12-13% -> Soju ~16-20% -> Whisky ~40% -> Vodka ~40%+ -> Absinthe
~55-74%), each tier from Beer up an equal 200-point band."""


def get_tier(score: int) -> EloTier:
    for threshold, tier in _TIER_THRESHOLDS:
        if score < threshold:
            return tier
    return "absinthe"


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


class CompletedMatchRow(TypedDict):
    team1_player_ids: list[str]
    team2_player_ids: list[str]
    winner: str
    elo_delta_team1: int | None
    elo_delta_team2: int | None


class PlayerStatRow(TypedDict):
    elo_score: int
    games: int
    wins: int
    draws: int
    losses: int


def reverse_match_results(
    matches: list[CompletedMatchRow], players_by_id: dict[UUID, PlayerStatRow]
) -> dict[UUID, PlayerStatRow]:
    """Undoes the elo_score/games/wins/draws/losses effect a set of completed
    matches had on their players — e.g. before deleting the session they
    belong to, so a deleted (test) session doesn't leave stats permanently
    skewed. Matches recorded before elo_delta_team1/2 existed (None) are
    skipped since there's nothing to undo them by."""
    updated: dict[UUID, PlayerStatRow] = {pid: dict(row) for pid, row in players_by_id.items()}  # type: ignore[misc]
    for match in matches:
        delta_team1, delta_team2 = match["elo_delta_team1"], match["elo_delta_team2"]
        if delta_team1 is None or delta_team2 is None:
            continue
        winner = match["winner"]
        team1_outcome = "win" if winner == "team1" else "draw" if winner == "draw" else "loss"
        team2_outcome = "win" if winner == "team2" else "draw" if winner == "draw" else "loss"
        for pid_str in match["team1_player_ids"]:
            _undo_one(updated, UUID(pid_str), delta_team1, team1_outcome)
        for pid_str in match["team2_player_ids"]:
            _undo_one(updated, UUID(pid_str), delta_team2, team2_outcome)
    return updated


def _undo_one(updated: dict[UUID, PlayerStatRow], pid: UUID, delta: int, outcome: str) -> None:
    row = updated.get(pid)
    if row is None:
        return
    row["elo_score"] = apply_delta(row["elo_score"], -delta)
    row["games"] = max(0, row["games"] - 1)
    if outcome == "win":
        row["wins"] = max(0, row["wins"] - 1)
    elif outcome == "draw":
        row["draws"] = max(0, row["draws"] - 1)
    else:
        row["losses"] = max(0, row["losses"] - 1)
