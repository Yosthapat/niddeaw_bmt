from uuid import UUID, uuid4

from app.services import matchmaking_service as mm


def _checked_in(scores: list[int]) -> tuple[list[UUID], list[mm.CheckedInPlayer]]:
    ids = [uuid4() for _ in scores]
    players = [mm.CheckedInPlayer(player_id=pid, elo_score=s) for pid, s in zip(ids, scores, strict=True)]
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


def test_cross_group_rotation_avoids_recent_partners_even_with_equal_elo() -> None:
    """Regression test for the "same 4 people keep getting grouped" report:
    with everyone at equal ELO (so elo_balance_score never breaks the tie),
    a player who's recently played with 3 others should end up in a
    different group as long as a zero-fairness-penalty alternative exists
    within the search window — not stuck rotating the same foursome's 3
    possible splits forever."""
    ids, players = _checked_in([1000] * 8)
    a, b, c, d, e, f, g, h = ids

    # a has recently teamed up with b and c, and faced off against d —
    # all within the fairness lookback window.
    history = [
        mm.PairHistoryEntry(player_a_id=a, player_b_id=b, relation="teammate", round_no=1),
        mm.PairHistoryEntry(player_a_id=a, player_b_id=c, relation="teammate", round_no=1),
        mm.PairHistoryEntry(player_a_id=a, player_b_id=d, relation="opponent", round_no=1),
    ]

    splits, waiting = mm.suggest_doubles_pairings(players, history, current_round=2)

    assert waiting == []
    a_group = next(s for s in splits if a in s.team1 or a in s.team2)
    a_groupmates = (set(a_group.team1) | set(a_group.team2)) - {a}
    assert a_groupmates == {e, f, g} or a_groupmates == {e, f, h} or a_groupmates == {e, g, h} or a_groupmates == {
        f,
        g,
        h,
    }
    assert not ({b, c, d} & a_groupmates)


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
    """"Highball, Highball vs Wine, Beer" — a 2-tier span (Beer to Wine) —
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
