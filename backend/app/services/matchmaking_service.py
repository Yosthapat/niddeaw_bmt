"""Auto-suggest ELO-balanced pairings with a basic anti-repeat fairness rule.

Pure functions operating on plain data (no Supabase calls here) so the
pairing logic itself is easy to reason about and unit-test; the router/
persistence layer fetches checked-in players + pairing_history rows and
passes them in.
"""

from dataclasses import dataclass
from itertools import combinations
from uuid import UUID

FAIRNESS_LOOKBACK_ROUNDS = 3
TEAMMATE_PENALTY = 3
OPPONENT_PENALTY = 1
FAIRNESS_WEIGHT = 20
DEFAULT_MATCH_DURATION_MINUTES = 15.0


@dataclass
class CheckedInPlayer:
    player_id: UUID
    elo_score: int


@dataclass
class PairHistoryEntry:
    player_a_id: UUID
    player_b_id: UUID
    relation: str  # "teammate" | "opponent"
    round_no: int


@dataclass
class Split:
    team1: tuple[UUID, ...]
    team2: tuple[UUID, ...]
    elo_balance_score: float
    fairness_penalty: float

    @property
    def total_cost(self) -> float:
        return self.elo_balance_score + self.fairness_penalty * FAIRNESS_WEIGHT


def _unordered_pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def _pairing_penalty(
    player_a: UUID, player_b: UUID, history: list[PairHistoryEntry], current_round: int
) -> float:
    penalty = 0.0
    pair = _unordered_pair(player_a, player_b)
    for entry in history:
        if entry.round_no <= current_round - FAIRNESS_LOOKBACK_ROUNDS:
            continue
        if _unordered_pair(entry.player_a_id, entry.player_b_id) != pair:
            continue
        penalty += TEAMMATE_PENALTY if entry.relation == "teammate" else OPPONENT_PENALTY
    return penalty


def _score_split(
    team1: tuple[UUID, ...],
    team2: tuple[UUID, ...],
    scores_by_id: dict[UUID, int],
    history: list[PairHistoryEntry],
    current_round: int,
) -> Split:
    team1_avg = sum(scores_by_id[p] for p in team1) / len(team1)
    team2_avg = sum(scores_by_id[p] for p in team2) / len(team2)

    fairness_penalty = 0.0
    for a, b in combinations(team1, 2):
        fairness_penalty += _pairing_penalty(a, b, history, current_round)
    for a, b in combinations(team2, 2):
        fairness_penalty += _pairing_penalty(a, b, history, current_round)
    for a in team1:
        for b in team2:
            fairness_penalty += _pairing_penalty(a, b, history, current_round)

    return Split(
        team1=team1,
        team2=team2,
        elo_balance_score=abs(team1_avg - team2_avg),
        fairness_penalty=fairness_penalty,
    )


def _best_split_for_group(
    group: tuple[UUID, ...],
    scores_by_id: dict[UUID, int],
    history: list[PairHistoryEntry],
    current_round: int,
) -> Split:
    p1, p2, p3, p4 = group
    candidate_splits = [
        ((p1, p2), (p3, p4)),
        ((p1, p3), (p2, p4)),
        ((p1, p4), (p2, p3)),
    ]
    scored = [
        _score_split(team1, team2, scores_by_id, history, current_round)
        for team1, team2 in candidate_splits
    ]
    return min(scored, key=lambda s: s.total_cost)


def suggest_doubles_pairings(
    checked_in: list[CheckedInPlayer],
    history: list[PairHistoryEntry],
    current_round: int,
) -> tuple[list[Split], list[UUID]]:
    """Returns (suggested splits, waiting player_ids) for doubles (groups of 4)."""
    sorted_players = sorted(checked_in, key=lambda p: p.elo_score, reverse=True)
    scores_by_id = {p.player_id: p.elo_score for p in sorted_players}

    splits: list[Split] = []
    ids = [p.player_id for p in sorted_players]
    i = 0
    while i + 4 <= len(ids):
        group = tuple(ids[i : i + 4])
        splits.append(_best_split_for_group(group, scores_by_id, history, current_round))
        i += 4

    waiting = ids[i:]
    return splits, waiting


def estimate_wait_minutes(queue_position: int, recent_durations_minutes: list[float]) -> float:
    avg = (
        sum(recent_durations_minutes) / len(recent_durations_minutes)
        if recent_durations_minutes
        else DEFAULT_MATCH_DURATION_MINUTES
    )
    return queue_position * avg


def build_pairing_history_rows(
    team1: tuple[UUID, ...], team2: tuple[UUID, ...], round_no: int
) -> list[dict[str, object]]:
    """One row per unordered pair among the match's players — teammates within
    each team, opponents across teams — used by future suggestions' fairness
    penalty lookback."""
    rows: list[dict[str, object]] = []
    for a, b in combinations(team1, 2):
        rows.append({"player_a_id": str(a), "player_b_id": str(b), "relation": "teammate", "round_no": round_no})
    for a, b in combinations(team2, 2):
        rows.append({"player_a_id": str(a), "player_b_id": str(b), "relation": "teammate", "round_no": round_no})
    for a in team1:
        for b in team2:
            rows.append({"player_a_id": str(a), "player_b_id": str(b), "relation": "opponent", "round_no": round_no})
    return rows
