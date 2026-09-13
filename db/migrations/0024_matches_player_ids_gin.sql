-- Per-player match lookups filter on "this player is in team1 OR team2",
-- which PostgREST expresses as
--   or=(team1_player_ids.cs.{uuid},team2_player_ids.cs.{uuid})
-- and Postgres as two array-containment predicates. Those columns are
-- uuid[] with no index, so every such lookup seq-scans the whole matches
-- table. Already the case for the profile page's nemesis breakdown
-- (backend/app/routers/public/players.py _fetch_own_matches), and now also
-- for the per-season match list on that same page.
--
-- Two separate GIN indexes rather than one composite: the predicate is an
-- OR across two independent columns, so the planner needs to be able to
-- scan each and BitmapOr the results together.
--
-- These serve the unpaginated full-history scan (nemesis). The paginated
-- season list also sorts by created_at desc, where the planner may well
-- prefer idx_matches_status_created_at (0019) and recheck the arrays
-- instead — that path is bounded by the session filter either way.
create index idx_matches_team1_player_ids on matches using gin (team1_player_ids);
create index idx_matches_team2_player_ids on matches using gin (team2_player_ids);

-- Seasons are resolved to a date range and then to the sessions inside it
-- (backend/app/services/season_service.py), so sessions is now filtered by
-- date on a read path. The daily ranking added in 0011's follow-up does the
-- same with an equality filter. Neither had an index on sessions.date.
create index idx_sessions_date on sessions (date);
