"""Auto-suggest doubles: who plays next by who has waited longest, then the
foursome and its teams that are closest in ELO without putting the same
people together again.

Members complained that on quieter nights the same two kept ending up as
partners or across the net from each other. Three things caused it, and
each has its rule here:

- Only the last few matches were remembered. Now the whole night is
  (pairing_history for this session), and repeats cost more the more often
  they happened.
- The same two are never partners more than TEAMMATE_LIMIT times a night,
  as long as any other way to fill the court exists.
- Whoever was free with the highest ELO went on next, so the strong players
  who had just come off kept going back on together. Now the ones who have
  waited longest go first; mixing in someone who just came off is allowed,
  at a price, when that is what it takes to avoid a repeat.

Pure functions on plain data (no Supabase calls here) so the pairing is easy
to reason about and unit-test; the router/persistence layer fetches the
checked-in players and pairing_history rows and passes them in.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from uuid import UUID

from app.models.player import EloTier
from app.services.elo_service import get_tier

FAIRNESS_WEIGHT = 20
"""One unit of fairness penalty is worth this many points of ELO difference
between the two teams' averages."""

TEAMMATE_LIMIT = 2
"""The same two people are partners at most this many times a night."""
TEAMMATE_PENALTY = 2.0
"""Partners again, for the second time (below the limit)."""
OVER_LIMIT_PENALTY = 500.0
"""Partners past TEAMMATE_LIMIT: chosen only when nothing else fills the court."""
OPPONENT_PENALTY = 1.2
"""Across the net again; grows faster than the number of meetings
(OPPONENT_PENALTY × times^1.5), so a fourth meeting costs far more than a
second."""
WAIT_PENALTY = 1.5
"""Putting someone on ahead of a free player who has waited longer, per
player passed over."""
EVEN_ENOUGH = 40.0
"""Teams' average ELO this close counts as an even match; past it, every
point of difference costs (1 + LOPSIDED_WEIGHT) times as much, so avoiding
a repeat never buys a lopsided game cheaply."""
LOPSIDED_WEIGHT = 5.0
DEFAULT_MATCH_DURATION_MINUTES = 15.0

TIER_ORDER: tuple[EloTier, ...] = (
    "milk",
    "beer",
    "highball",
    "wine",
    "soju",
    "whisky",
    "vodka",
    "absinthe",
)
_TIER_RANK = {tier: rank for rank, tier in enumerate(TIER_ORDER)}

MAX_TIER_SPAN = 2
"""An auto-suggested group of 4 (not an admin-locked pair) never spans more
than this many tiers between its highest- and lowest-ranked player — e.g.
Highball + Wine (span 1) is fine, but Milk grouped with Highball and Wine
(span 3) is the lopsided kind of match members were complaining about.
Locked pairs are a deliberate admin override and stay exempt (see
_complete_locked_pair) — the cap is only for the organic grouping below."""


def _tier_rank(score: int) -> int:
    return _TIER_RANK[get_tier(score)]


def _group_tier_span(group: tuple[UUID, ...], scores_by_id: dict[UUID, int]) -> int:
    ranks = [_tier_rank(scores_by_id[pid]) for pid in group]
    return max(ranks) - min(ranks)


GROUP_SEARCH_WINDOW = 10
"""How many of the free players, longest-waiting first, a group of 4 is
picked from. Wider than 4 so the repeat rules can change *who* plays
together, not only how a fixed foursome splits into teams; narrow enough
that someone who has waited is not passed over for long."""


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
        lopsided = max(0.0, self.elo_balance_score - EVEN_ENOUGH)
        return (
            self.elo_balance_score
            + LOPSIDED_WEIGHT * lopsided
            + self.fairness_penalty * FAIRNESS_WEIGHT
        )


def _pair(a: UUID, b: UUID) -> frozenset[UUID]:
    return frozenset((a, b))


@dataclass
class Tonight:
    """What tonight's matches so far add up to, per pair and per player."""

    teammates: Counter[frozenset[UUID]] = field(default_factory=Counter)
    opponents: Counter[frozenset[UUID]] = field(default_factory=Counter)
    games: Counter[UUID] = field(default_factory=Counter)
    last_round: dict[UUID, int] = field(default_factory=dict)

    @classmethod
    def from_history(cls, history: list[PairHistoryEntry]) -> "Tonight":
        night = cls()
        played: set[tuple[UUID, int]] = set()
        for entry in history:
            pair = _pair(entry.player_a_id, entry.player_b_id)
            if entry.relation == "teammate":
                night.teammates[pair] += 1
            else:
                night.opponents[pair] += 1
            for pid in (entry.player_a_id, entry.player_b_id):
                if (pid, entry.round_no) not in played:
                    played.add((pid, entry.round_no))
                    night.games[pid] += 1
                night.last_round[pid] = max(night.last_round.get(pid, 0), entry.round_no)
        return night

    def teammate_cost(self, a: UUID, b: UUID) -> float:
        times = self.teammates[_pair(a, b)]
        if times >= TEAMMATE_LIMIT:
            return OVER_LIMIT_PENALTY
        return TEAMMATE_PENALTY * times

    def opponent_cost(self, a: UUID, b: UUID) -> float:
        times = float(self.opponents[_pair(a, b)])
        return OPPONENT_PENALTY * times * math.sqrt(times)


def _score_split(
    team1: tuple[UUID, ...],
    team2: tuple[UUID, ...],
    scores_by_id: dict[UUID, int],
    tonight: Tonight,
) -> Split:
    team1_avg = sum(scores_by_id[p] for p in team1) / len(team1)
    team2_avg = sum(scores_by_id[p] for p in team2) / len(team2)

    fairness_penalty = 0.0
    for team in (team1, team2):
        for a, b in combinations(team, 2):
            fairness_penalty += tonight.teammate_cost(a, b)
    for a in team1:
        for b in team2:
            fairness_penalty += tonight.opponent_cost(a, b)

    return Split(
        team1=team1,
        team2=team2,
        elo_balance_score=abs(team1_avg - team2_avg),
        fairness_penalty=fairness_penalty,
    )


def _best_split_for_group(
    group: tuple[UUID, ...], scores_by_id: dict[UUID, int], tonight: Tonight
) -> Split:
    p1, p2, p3, p4 = group
    candidate_splits = [
        ((p1, p2), (p3, p4)),
        ((p1, p3), (p2, p4)),
        ((p1, p4), (p2, p3)),
    ]
    scored = [
        _score_split(team1, team2, scores_by_id, tonight) for team1, team2 in candidate_splits
    ]
    return min(scored, key=lambda s: s.total_cost)


def _passed_over(group: tuple[UUID, ...], pool: list[UUID]) -> int:
    """How many times a player in the group goes on ahead of someone left out
    who was ahead of them in the queue (pool is in queue order)."""
    place = {pid: i for i, pid in enumerate(pool)}
    left_out = [place[pid] for pid in pool if pid not in group]
    return sum(1 for pid in group for out in left_out if out < place[pid])


def _best_group_from_pool(
    anchor: UUID,
    pool: list[UUID],
    scores_by_id: dict[UUID, int],
    tonight: Tonight,
) -> tuple[tuple[UUID, ...], Split] | None:
    """Tries every foursome of anchor + 3 players from pool whose tier span
    stays within MAX_TIER_SPAN, returning the cheapest group and its 2v2
    split — or None if no foursome in pool satisfies the tier cap. The
    split's fairness penalty includes passing over players who waited
    longer, so the queue is kept unless keeping it means a repeat."""
    queue = [anchor, *pool]
    best_group: tuple[UUID, ...] | None = None
    best_split: Split | None = None
    for trio in combinations(pool, 3):
        group = (anchor, *trio)
        if _group_tier_span(group, scores_by_id) > MAX_TIER_SPAN:
            continue
        split = _best_split_for_group(group, scores_by_id, tonight)
        split.fairness_penalty += WAIT_PENALTY * _passed_over(group, queue)
        if best_split is None or split.total_cost < best_split.total_cost:
            best_group, best_split = group, split
    if best_group is None or best_split is None:
        return None
    return best_group, best_split


def _complete_locked_pair(
    pair: tuple[UUID, UUID],
    remaining: list[UUID],
    other_active_locks: list[tuple[UUID, UUID]],
    scores_by_id: dict[UUID, int],
    tonight: Tonight,
) -> Split | None:
    """Finds the best opponents to complete a locked pair's group of 4 —
    either two solo (unlocked) players, or one other complete locked pair
    faced off against them. Never splits any locked pair across teams.
    Returns None if there aren't enough other players available yet."""
    other_locked_member_ids = {pid for other in other_active_locks for pid in other}
    solo_candidates = [
        pid for pid in remaining if pid not in pair and pid not in other_locked_member_ids
    ]

    best: Split | None = None
    for duo in combinations(solo_candidates[:GROUP_SEARCH_WINDOW], 2):
        split = _score_split(pair, duo, scores_by_id, tonight)
        if best is None or split.total_cost < best.total_cost:
            best = split

    for other in other_active_locks:
        if other[0] in remaining and other[1] in remaining:
            split = _score_split(pair, other, scores_by_id, tonight)
            if best is None or split.total_cost < best.total_cost:
                best = split

    return best


def suggest_doubles_pairings(
    checked_in: list[CheckedInPlayer],
    history: list[PairHistoryEntry],
    current_round: int,
    locked_pairs: tuple[tuple[UUID, UUID], ...] = (),
) -> tuple[list[Split], list[UUID]]:
    """Returns (suggested splits, waiting player_ids) for doubles (groups of 4).

    history is tonight's pairing_history; current_round is kept for callers
    but the whole night counts the same.

    locked_pairs are admin-pinned teammates for this session (e.g. two
    friends who came together today) — each is always kept on the same
    team, matched against either two solo players or one other complete
    locked pair, never split up. Pairs where either member isn't currently
    checked in are ignored.

    Everyone else queues by how long they have waited: the last match they
    played longest ago first (not played yet tonight: first of all), then
    fewer games, then higher ELO, which is the order the old suggestion
    used when nobody has played. The front of the queue anchors a group,
    and its 3 groupmates come from the next GROUP_SEARCH_WINDOW in the
    queue, whichever foursome and split costs least.
    """
    tonight = Tonight.from_history(history)
    scores_by_id = {p.player_id: p.elo_score for p in checked_in}
    all_ids = set(scores_by_id)
    remaining = sorted(
        scores_by_id,
        key=lambda pid: (tonight.last_round.get(pid, 0), tonight.games[pid], -scores_by_id[pid]),
    )

    active_locks = [pair for pair in locked_pairs if pair[0] in all_ids and pair[1] in all_ids]

    splits: list[Split] = []
    for pair in active_locks:
        if pair[0] not in remaining or pair[1] not in remaining:
            continue  # already used as another lock's opponents this round
        other_locks = [
            p for p in active_locks if p != pair and p[0] in remaining and p[1] in remaining
        ]
        split = _complete_locked_pair(pair, remaining, other_locks, scores_by_id, tonight)
        if split is None:
            continue  # not enough other players checked in to complete this group yet
        splits.append(split)
        used = set(split.team1) | set(split.team2)
        remaining = [pid for pid in remaining if pid not in used]

    tier_capped_waiting: list[UUID] = []
    while len(remaining) >= 4:
        anchor, *rest = remaining
        pool = rest[: GROUP_SEARCH_WINDOW - 1]
        result = _best_group_from_pool(anchor, pool, scores_by_id, tonight)
        if result is None:
            # The window didn't contain a tier-eligible trio — widen to
            # every remaining player within the tier cap before giving up
            # on this anchor for the round.
            anchor_rank = _tier_rank(scores_by_id[anchor])
            tier_eligible = [
                pid
                for pid in rest
                if abs(_tier_rank(scores_by_id[pid]) - anchor_rank) <= MAX_TIER_SPAN
            ]
            if len(tier_eligible) >= 3:
                result = _best_group_from_pool(anchor, tier_eligible, scores_by_id, tonight)
        if result is None:
            # No tier-eligible foursome available yet — this player waits
            # rather than getting matched across a lopsided tier gap.
            tier_capped_waiting.append(anchor)
            remaining = rest
            continue
        group, split = result
        splits.append(split)
        remaining = [pid for pid in remaining if pid not in group]

    return splits, tier_capped_waiting + remaining


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
        rows.append(
            {
                "player_a_id": str(a),
                "player_b_id": str(b),
                "relation": "teammate",
                "round_no": round_no,
            }
        )
    for a, b in combinations(team2, 2):
        rows.append(
            {
                "player_a_id": str(a),
                "player_b_id": str(b),
                "relation": "teammate",
                "round_no": round_no,
            }
        )
    for a in team1:
        for b in team2:
            rows.append(
                {
                    "player_a_id": str(a),
                    "player_b_id": str(b),
                    "relation": "opponent",
                    "round_no": round_no,
                }
            )
    return rows
