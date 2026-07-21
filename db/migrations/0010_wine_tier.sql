-- Insert a "Wine" ELO tier and reorder every tier by rising alcohol content
-- (Milk 0% -> Beer ~5% -> Highball ~7-9% -> Wine ~12-13% -> Soju ~16-20% ->
-- Whisky ~40% -> Vodka ~40%+), matching the reordered thresholds in
-- backend/app/services/elo_service.py's _TIER_THRESHOLDS.
--
-- Unlike 0007_whisky_tier.sql, production now has real players, so this
-- also recomputes elo_level for every existing row — the tier *names*
-- attached to each score band changed even though the band boundaries
-- (900/1100/1300/1500/1700) stayed the same width, so a player's stored
-- elo_level would otherwise be stale until their next match.

alter table players drop constraint players_elo_level_check;
alter table players add constraint players_elo_level_check
    check (elo_level in ('milk', 'beer', 'highball', 'wine', 'soju', 'whisky', 'vodka'));

update players set elo_level = case
    when elo_score < 900 then 'milk'
    when elo_score < 1100 then 'beer'
    when elo_score < 1300 then 'highball'
    when elo_score < 1500 then 'wine'
    when elo_score < 1700 then 'soju'
    when elo_score < 1900 then 'whisky'
    else 'vodka'
end;
