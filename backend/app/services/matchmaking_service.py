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

GROUP_SEARCH_WINDOW = 7
"""When forming a group of 4 around the highest-remaining-ELO player, how
many of the next-closest-ELO remaining players are considered as
candidate groupmates — not rigidly just the next 3. A small, ELO-stable
checked-in pool otherwise keeps reforming the exact same foursome round
after round, leaving only 3 possible 2v2 splits to rotate between no
matter how good the fairness penalty is. Widening the pool lets the
penalty actually influence *who* gets grouped, not just how a fixed
foursome splits into teams."""


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


def _best_group_from_pool(
    anchor: UUID,
    pool: list[UUID],
    scores_by_id: dict[UUID, int],
    history: list[PairHistoryEntry],
    current_round: int,
) -> tuple[tuple[UUID, ...], Split]:
    """Tries every foursome of anchor + 3 players from pool (pool always has
    at least 3, since it's only called when len(remaining) >= 4), returns
    the group and its lowest-cost 2v2 split."""
    best_group: tuple[UUID, ...] | None = None
    best_split: Split | None = None
    for trio in combinations(pool, 3):
        group = (anchor, *trio)
        split = _best_split_for_group(group, scores_by_id, history, current_round)
        if best_split is None or split.total_cost < best_split.total_cost:
            best_group, best_split = group, split
    assert best_group is not None and best_split is not None
    return best_group, best_split


def suggest_doubles_pairings(
    checked_in: list[CheckedInPlayer],
    history: list[PairHistoryEntry],
    current_round: int,
) -> tuple[list[Split], list[UUID]]:
    """Returns (suggested splits, waiting player_ids) for doubles (groups of 4).

    Groups are formed one at a time: the highest-ELO remaining player
    anchors a group, and its 3 groupmates are chosen from a window of the
    next GROUP_SEARCH_WINDOW closest-ELO remaining players — not rigidly
    the next 3 — picking whichever foursome+split combination has the
    lowest total cost. See GROUP_SEARCH_WINDOW's docstring for why.
    """
    sorted_players = sorted(checked_in, key=lambda p: p.elo_score, reverse=True)
    scores_by_id = {p.player_id: p.elo_score for p in sorted_players}
    remaining = [p.player_id for p in sorted_players]

    splits: list[Split] = []
    while len(remaining) >= 4:
        anchor, *rest = remaining
        pool = rest[:GROUP_SEARCH_WINDOW]
        group, split = _best_group_from_pool(anchor, pool, scores_by_id, history, current_round)
        splits.append(split)
        remaining = [pid for pid in remaining if pid not in group]

    return splits, remaining


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
