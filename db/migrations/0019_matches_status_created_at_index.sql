-- The public /api/matches list (no session_id filter — it's the global
-- match log, not a per-session view) filters on status and sorts by
-- created_at desc. The existing matches indexes are all keyed on
-- session_id, so this query falls back to a full-table scan + sort that
-- gets slower every month as match history accumulates.

create index idx_matches_status_created_at on matches (status, created_at desc);
