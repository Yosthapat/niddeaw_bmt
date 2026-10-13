"""Checks every player's record on their profile against the matches.

A profile's "เกม / ชนะ / เสมอ / แพ้" comes from counters on the player's own
row, kept up to date as results are recorded, not from counting the match
rows. This recomputes each player's record from the completed matches and
prints every player where the two disagree.

Before suspecting the counters, note that the profile's figure is the
club's **whole history**: "he only played 7 tonight" and "it says 10" are
both true if three were an earlier night. `--player` prints that
breakdown, night by night, so you can tell which it is.

    # check everyone, change nothing
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        backend/.venv/bin/python tools/recount_stats.py

    # one player, game by game, night by night
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        backend/.venv/bin/python tools/recount_stats.py --player Aekk

    # write the recomputed records back
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        backend/.venv/bin/python tools/recount_stats.py --apply

The repair overwrites rather than adjusts, so running it twice changes
nothing the second time. ELO is never touched: a rating depends on the
order its matches were played in and on the ratings at the time, so it
cannot be recomputed from the same rows. Needs the backend's own
environment (backend/.venv).
"""

from __future__ import annotations

import argparse
import os
import sys
from uuid import UUID

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.db_utils import rows  # noqa: E402
from app.services.stats_audit import audit, spells  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the recomputed records back; without it nothing is written",
    )
    parser.add_argument(
        "--player",
        metavar="NAME",
        help="print this player's games night by night instead of auditing everyone",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    from supabase import create_client

    supabase = create_client(url, key)

    if args.player:
        found = rows(
            supabase.table("players")
            .select("id,nickname,games,wins,draws,losses")
            .ilike("nickname", args.player)
            .execute()
        )
        if not found:
            sys.exit(f'no member called "{args.player}"')
        player = found[0]
        nights = spells(supabase, UUID(str(player["id"])))
        print(f"{player['nickname']} — profile says {player['games']} games\n")
        for night in nights:
            print(f"  {night.date or night.session_id:12} {night.games} games")
        total = sum(n.games for n in nights)
        print(f"\n  {'in the matches':12} {total} games across {len(nights)} night(s)")
        if total != int(player["games"]):
            print(
                f"\n  the profile is {int(player['games']) - total:+d} out of step with the "
                f"matches — run without --player to see everyone, then --apply to fix"
            )
        else:
            print("\n  the profile matches the match history exactly")
        return 0

    report = audit(supabase, apply=args.apply)

    if report.rows:
        print(f"{'member':20} {'games':>13} {'W':>9} {'D':>9} {'L':>9}")
        for row in report.rows:
            mark = " (ลบแล้ว)" if not row.is_active else ""
            print(
                f"{row.nickname + mark:20} "
                f"{row.stored_games:5} -> {row.real_games:<5} "
                f"{row.stored_wins:3} -> {row.real_wins:<3} "
                f"{row.stored_draws:3} -> {row.real_draws:<3} "
                f"{row.stored_losses:3} -> {row.real_losses:<3}"
            )

    print(
        f"\n{report.players_checked} players checked against {report.matches_counted} "
        f"completed matches\n{len(report.rows)} with a record that does not match"
    )
    if report.orphan_player_ids:
        print(
            f"\n! {len(report.orphan_player_ids)} player id(s) on matches are not in the "
            "players table at all — those games count for nobody:"
        )
        for pid in report.orphan_player_ids:
            print(f"    {pid}")
    if report.rows and not report.applied:
        print("\nnothing was written — re-run with --apply")
    elif report.applied and report.rows:
        print("\nwritten. ELO was left alone (it cannot be recomputed from the same rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
