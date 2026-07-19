-- Indexes supporting the app's hot-path queries (checked-in lookups,
-- ranking sort, matchmaking fairness lookback).

-- "Who's currently checked in for this session" — partial index since
-- checkout_time IS NULL is the only filter this query ever uses.
create index idx_checkins_active_by_session
    on checkins (session_id)
    where checkout_time is null;

create index idx_players_elo_score_desc on players (elo_score desc);

create index idx_matches_session on matches (session_id);
create index idx_matches_session_status on matches (session_id, status);

create index idx_billings_session on billings (session_id);

create index idx_pairing_history_session_round
    on pairing_history (session_id, round_no desc);
