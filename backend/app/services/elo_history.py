"""What each team's ELO was going into a finished match.

The club only stores the change a result made (matches.elo_delta_team1/2),
not the ratings it was made from. They can be worked back: start from every
player's rating now and walk the finished matches newest first, taking each
match's change back off its players. What is left at each step is what they
had going into that match. Doubles teams are rated by their average, as
elo_service rates them.

This is exact as long as ratings only ever moved by recorded results. An
admin's hand edit, or the floor (SCORE_FLOOR) holding a rating up, makes
the older numbers approximate; they are for a gauge, not for the ledger.
"""

from typing import Any
from uuid import UUID

from supabase import Client

from app.db_utils import rows
from app.services.elo_service import team_rating

Team = tuple[float, float]


def before_ratings(supabase: Client) -> dict[str, Team]:
    """Match id -> (team 1's average, team 2's average) going into it, for
    every finished match whose change was recorded."""
    current = {
        str(p["id"]): int(p["elo_score"])
        for p in rows(supabase.table("players").select("id,elo_score").execute())
    }
    finished = rows(
        supabase.table("matches")
        .select(
            "id,team1_player_ids,team2_player_ids,elo_delta_team1,elo_delta_team2,created_at,updated_at"
        )
        .eq("status", "completed")
        .execute()
    )
    # The result that was saved last is the last one applied.
    finished.sort(
        key=lambda m: (str(m.get("updated_at") or ""), str(m.get("created_at") or "")), reverse=True
    )
    out: dict[str, Team] = {}
    for m in finished:
        d1, d2 = m.get("elo_delta_team1"), m.get("elo_delta_team2")
        if d1 is None or d2 is None:
            continue
        t1 = [str(p) for p in m.get("team1_player_ids") or []]
        t2 = [str(p) for p in m.get("team2_player_ids") or []]
        if not t1 or not t2 or any(p not in current for p in t1 + t2):
            continue
        for p in t1:
            current[p] -= int(d1)
        for p in t2:
            current[p] -= int(d2)
        out[str(m["id"])] = (
            team_rating([current[p] for p in t1]),
            team_rating([current[p] for p in t2]),
        )
    return out


def current_ratings(supabase: Client, team1: list[UUID], team2: list[UUID]) -> Team | None:
    """Each team's average now, for a match not yet played."""
    ids = [str(p) for p in team1 + team2]
    if not team1 or not team2:
        return None
    found = {
        str(p["id"]): int(p["elo_score"])
        for p in rows(supabase.table("players").select("id,elo_score").in_("id", ids).execute())
    }
    if any(p not in found for p in ids):
        return None
    return (
        team_rating([found[str(p)] for p in team1]),
        team_rating([found[str(p)] for p in team2]),
    )


def with_ratings(match: dict[str, Any], ratings: dict[str, Team]) -> dict[str, Any]:
    """The match row with elo_team1/elo_team2 filled in, when known."""
    got = ratings.get(str(match["id"]))
    if got is None:
        return match
    return {**match, "elo_team1": round(got[0], 1), "elo_team2": round(got[1], 1)}
