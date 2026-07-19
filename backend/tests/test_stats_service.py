from uuid import UUID, uuid4

from app.services import stats_service

P1, P2, P3, P4 = (str(uuid4()) for _ in range(4))


def _match(team1: list[str], team2: list[str], winner: str) -> stats_service.CompletedMatchRow:
    return {"team1_player_ids": team1, "team2_player_ids": team2, "winner": winner}


def test_find_nemesis_picks_most_frequent_opponent() -> None:
    matches = [
        _match([P1], [P2], "team1"),
        _match([P1], [P2], "team2"),
        _match([P1], [P3], "team1"),
    ]
    result = stats_service.find_nemesis(UUID(P1), matches)
    assert result is not None
    nemesis_id, record = result
    assert nemesis_id == UUID(P2)
    assert record.encounters == 2
    assert record.wins == 1
    assert record.losses == 1


def test_find_nemesis_counts_both_doubles_opponents() -> None:
    matches = [_match([P1, P4], [P2, P3], "team1")]
    result = stats_service.find_nemesis(UUID(P1), matches)
    assert result is not None
    # Both P2 and P3 have 1 encounter each — max() picks whichever comes
    # first, but either is a valid nemesis and must show the win counted.
    nemesis_id, record = result
    assert nemesis_id in (UUID(P2), UUID(P3))
    assert record.encounters == 1
    assert record.wins == 1


def test_find_nemesis_none_when_player_has_no_matches() -> None:
    assert stats_service.find_nemesis(UUID(P1), []) is None


def test_find_nemesis_handles_draws() -> None:
    matches = [_match([P1], [P2], "draw")]
    result = stats_service.find_nemesis(UUID(P1), matches)
    assert result is not None
    _, record = result
    assert record.draws == 1
    assert record.wins == 0
    assert record.losses == 0
