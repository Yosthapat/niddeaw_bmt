# Active Context

## Current Task
- Full stats-denormalization + /members pagination implemented — pushing now

## Done Last Session
- User asked for both the quick pagination fix AND the sustainable fix (not deferred) after I laid out the tradeoff
- Denormalized games/wins/draws/losses onto the `players` table (db/migrations/0011_denormalize_player_stats.sql, with a backfill CTE — currently a no-op since match history was already cleaned to zero):
  - `submit_result` (admin/matchmaking.py) now increments these 4 counters for both teams in the same select+update round trip already used for elo_score — no extra DB calls
  - Every read path that used to call `stats_service.build_player_records()` over a full match-history scan now builds a `PlayerRecord` straight from a player's own stored counters instead: public players.py (list_players, get_player_profile's own stats), matches.py (get_match_detail's PlayerMatchStat), hall_of_fame.py, ranking.py's period=all branch
  - Exception: ranking's period=year still does a live scan (bounded to ~1 year of matches, not the whole club history — not worth year-bucketed denormalization yet)
  - Player profile's nemesis calc (needs a per-opponent breakdown) now scopes its matches query to just that player's own games via a `.or_()` + `cs.` (array-contains) filter, instead of fetching every completed match site-wide
- `/api/players` gained optional `limit`/`offset` query params + moved sorting (by points desc) server-side; omitting both (as MatchHistoryView.vue/LiveView.vue's existing name-lookup calls do) still returns the full roster unchanged — fully backward compatible
- `MemberListView.vue`: paginated like `/matches` (20 at a time, "load more" button) for the default browse view; typing in the search box triggers one full-roster fetch (since search needs to find anyone, not just what's paged in so far) and disables further pagination while searching
- Added `games/wins/draws/losses` to the frontend `Player` type for consistency (harmless additive change, nothing currently reads them off `Player` directly — components use the nested `PlayerStats`/`PlayerProfile` top-level fields)
- Backend mypy + pytest (25/25) and frontend vue-tsc + vite build clean

## Next Steps
- Push code, then give the user the 0011 migration SQL to run in Supabase
- After migration runs: verify end-to-end against prod — submit a throwaway match result, confirm games/wins/etc increment correctly on the player record, confirm /members, /matches detail, ranking, hall-of-fame all still render correctly, then clean up the throwaway data

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-23

## Checkpoint (auto)
- 00:31 — edited active.md
- 00:21 — edited active.md