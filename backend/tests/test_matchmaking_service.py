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
