-- Insert a "Whisky" ELO tier between Beer and Highball, narrowing their
-- score bands (see backend/app/services/elo_service.py's updated
-- _TIER_THRESHOLDS). Safe to run now — production currently has zero real
-- players (QA test data was cleaned up), so no live player's tier changes
-- as a side effect of this migration.

alter table players drop constraint players_elo_level_check;
alter table players add constraint players_elo_level_check
    check (elo_level in ('milk', 'soju', 'beer', 'whisky', 'highball', 'vodka'));
