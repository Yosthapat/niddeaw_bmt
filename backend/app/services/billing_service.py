"""Billing math: per-game cost derivation and effective-amount resolution.

Pure functions — no Supabase I/O — so the formula can be unit-tested
directly. Each player who attends a session pays a flat court fee once,
plus a flat shuttlecock cost per game they actually played (not split
between teammates/opponents). Check-in/checkout times are still recorded
for attendance and the matchmaking queue, but no longer feed into billing.
"""


def compute_amount_calc(
    game_count: int, court_fee_per_person: float, shuttlecock_price_per_game: float
) -> float:
    return round(court_fee_per_person + game_count * shuttlecock_price_per_game, 2)


def count_games_played(player_id: str, matches: list[dict[str, list[str]]]) -> int:
    """Counts completed matches (singles or doubles) `player_id` appears in."""
    return sum(
        1
        for match in matches
        if player_id in [*match["team1_player_ids"], *match["team2_player_ids"]]
    )


def effective_amount(amount_calc: float, amount_adjusted: float | None) -> float:
    return amount_adjusted if amount_adjusted is not None else amount_calc
