import random
from collections import Counter
from uuid import UUID, uuid4

from app.services import matchmaking_service as mm


def _checked_in(scores: list[int]) -> tuple[list[UUID], list[mm.CheckedInPlayer]]:
    ids = [uuid4() for _ in scores]
    players = [
        mm.CheckedInPlayer(player_id=pid, elo_score=s) for pid, s in zip(ids, scores, strict=True)
    ]
    return ids, players


def test_no_history_still_groups_by_closest_elo() -> None:
    """With no fairness pressure, the search-window widening shouldn't
    change the baseline behavior: clearly-separated ELO clusters should
    still group together."""
    ids, players = _checked_in([2000, 1900, 1800, 1700, 500, 400, 300, 200])
    top4, bottom4 = ids[:4], ids[4:]

    splits, waiting = mm.suggest_doubles_pairings(players, history=[], current_round=1)

    assert waiting == []
    assert len(splits) == 2
    for split in splits:
        group = set(split.team1) | set(split.team2)
        assert group == set(top4) or group == set(bottom4)


def _played(
    team1: tuple[UUID, ...], team2: tuple[UUID, ...], round_no: int
) -> list[mm.PairHistoryEntry]:
    return [
        mm.PairHistoryEntry(
            UUID(r["player_a_id"]), UUID(r["player_b_id"]), str(r["relation"]), round_no
        )
        for r in mm.build_pairing_history_rows(team1, team2, round_no)
    ]


def _together(split: mm.Split, a: UUID, b: UUID) -> bool:
    return {a, b} <= set(split.team1) or {a, b} <= set(split.team2)


def test_those_who_waited_go_on_before_those_who_just_came_off() -> None:
    """Regression test for "the same 4 keep playing": a, b, c, d just
    played; e, f, g, h have been waiting. The next court goes to the four
    who waited, even though the others are the stronger players."""
    ids, players = _checked_in([1300, 1300, 1300, 1300, 1000, 1000, 1000, 1000])
    a, b, c, d, e, f, g, h = ids

    splits, waiting = mm.suggest_doubles_pairings(
        players, _played((a, b), (c, d), 1), current_round=2
    )

    assert waiting == []
    first = splits[0]
    assert set(first.team1) | set(first.team2) == {e, f, g, h}
    # and the four who just played do not get the same partners again
    assert not _together(splits[1], a, b) and not _together(splits[1], c, d)


def test_partners_from_early_in_the_night_are_still_remembered() -> None:
    """The old rule forgot anything older than the last 3 matches; partners
    from the first match of the night count just as much at match 20."""
    ids, players = _checked_in([1000] * 4)
    a, b, c, d = ids

    splits, _ = mm.suggest_doubles_pairings(players, _played((a, b), (c, d), 1), current_round=20)

    assert not _together(splits[0], a, b)
    assert not _together(splits[0], c, d)


def test_the_same_two_are_never_partners_a_third_time_while_there_is_another_way() -> None:
    ids, players = _checked_in([1000] * 4)
    a, b, c, d = ids
    # a+b have partnered twice already; a+c and a+d once each
    history = (
        _played((a, b), (c, d), 1) + _played((a, b), (c, d), 2) + _played((a, c), (b, d), 3)
        + _played((a, d), (b, c), 4)
    )  # fmt: skip

    splits, _ = mm.suggest_doubles_pairings(players, history, current_round=5)

    assert not _together(splits[0], a, b)


def test_a_quiet_night_spreads_partners_games_and_keeps_matches_even() -> None:
    """12 players on 2 courts for 40 matches, the admin always taking the
    first suggestion: nobody partners anyone more than twice, everyone's
    games stay within 3 of each other, and the teams stay close in ELO."""
    rnd = random.Random(7)
    ids, players = _checked_in([int(rnd.gauss(1150, 150)) for _ in range(12)])
    history: list[mm.PairHistoryEntry] = []
    playing: list[set[UUID]] = []
    partners: Counter[frozenset[UUID]] = Counter()
    games: Counter[UUID] = Counter()
    gaps: list[float] = []
    for round_no in range(1, 41):
        if len(playing) == 2:
            playing.pop(0)  # the court that started first is the one that frees
        busy = set().union(*playing) if playing else set()
        free = [p for p in players if p.player_id not in busy]
        splits, _ = mm.suggest_doubles_pairings(free, history, round_no)
        split = splits[0]
        history += _played(split.team1, split.team2, round_no)
        partners[frozenset(split.team1)] += 1
        partners[frozenset(split.team2)] += 1
        for pid in (*split.team1, *split.team2):
            games[pid] += 1
        gaps.append(split.elo_balance_score)
        playing.append(set(split.team1) | set(split.team2))

    assert max(partners.values()) <= mm.TEAMMATE_LIMIT
    assert max(games[p] for p in ids) - min(games[p] for p in ids) <= 3
    assert sum(gaps) / len(gaps) < 60


def test_locked_pair_always_stays_on_the_same_team() -> None:
    """Two friends locked together should never end up split across teams,
    even when that would otherwise be the better ELO-balance choice."""
    ids, players = _checked_in([2000, 1000, 1500, 1500])
    a, b, c, d = ids  # a+b locked despite being the most mismatched ELOs

    splits, waiting = mm.suggest_doubles_pairings(
        players, history=[], current_round=1, locked_pairs=((a, b),)
    )

    assert waiting == []
    assert len(splits) == 1
    split = splits[0]
    assert (a in split.team1 and b in split.team1) or (a in split.team2 and b in split.team2)
    assert set(split.team1) | set(split.team2) == {a, b, c, d}


def test_two_locked_pairs_face_off_without_splitting_either() -> None:
    ids, players = _checked_in([1000] * 4)
    a, b, c, d = ids

    splits, waiting = mm.suggest_doubles_pairings(
        players, history=[], current_round=1, locked_pairs=((a, b), (c, d))
    )

    assert waiting == []
    assert len(splits) == 1
    split = splits[0]
    ab_together = (a in split.team1 and b in split.team1) or (a in split.team2 and b in split.team2)
    cd_together = (c in split.team1 and d in split.team1) or (c in split.team2 and d in split.team2)
    assert ab_together
    assert cd_together


def test_locked_pair_ignored_when_a_member_is_not_checked_in() -> None:
    ids, players = _checked_in([1000] * 4)
    a, b, c, d = ids
    missing = UUID(int=0)

    splits, waiting = mm.suggest_doubles_pairings(
        players, history=[], current_round=1, locked_pairs=((a, missing),)
    )

    assert waiting == []
    assert len(splits) == 1
    group = set(splits[0].team1) | set(splits[0].team2)
    assert group == {a, b, c, d}


def test_locked_pair_waits_together_when_not_enough_others_checked_in() -> None:
    ids, players = _checked_in([1000, 1000, 1000])
    a, b, c = ids

    splits, waiting = mm.suggest_doubles_pairings(
        players, history=[], current_round=1, locked_pairs=((a, b),)
    )

    assert splits == []
    assert set(waiting) == {a, b, c}


def test_wide_tier_gap_waits_instead_of_matching() -> None:
    """Regression test for the "Wine+Milk vs Highball+Beer" report: a
    foursome spanning 3 tiers (Milk to Wine) is exactly the ELO-balanced
    split the old algorithm loved (avg 1100 vs avg 1100) — it's now
    rejected outright and everyone waits rather than playing a lopsided
    game."""
    ids, players = _checked_in([1400, 800, 1200, 1000])  # wine, milk, highball, beer

    splits, waiting = mm.suggest_doubles_pairings(players, history=[], current_round=1)

    assert splits == []
    assert set(waiting) == set(ids)


def test_two_tier_gap_is_the_allowed_boundary() -> None:
    """ "Highball, Highball vs Wine, Beer" — a 2-tier span (Beer to Wine) —
    is the user-confirmed OK case: it should still get matched."""
    ids, players = _checked_in([1200, 1200, 1400, 1000])  # highball, highball, wine, beer

    splits, waiting = mm.suggest_doubles_pairings(players, history=[], current_round=1)

    assert waiting == []
    assert len(splits) == 1
    assert set(splits[0].team1) | set(splits[0].team2) == set(ids)


def test_tier_incompatible_players_wait_while_compatible_ones_still_match() -> None:
    """A player too far (tier-wise) from everyone else should wait rather
    than drag tier-compatible players into a lopsided foursome with them —
    and should still show up in the waiting list, not vanish."""
    ids, players = _checked_in([2000, 800, 1450, 1400, 1350, 1300])
    vodka, milk, wine1, wine2, wine3, wine4 = ids

    splits, waiting = mm.suggest_doubles_pairings(players, history=[], current_round=1)

    assert set(waiting) == {vodka, milk}
    assert len(splits) == 1
    assert set(splits[0].team1) | set(splits[0].team2) == {wine1, wine2, wine3, wine4}
