-- Insert an "Absinthe" ELO tier above Vodka as the new highest tier
-- (Milk 0% -> Beer ~5% -> Highball ~7-9% -> Wine ~12-13% -> Soju ~16-20% ->
-- Whisky ~40% -> Vodka ~40%+ -> Absinthe ~55-74%), matching the updated
-- thresholds in backend/app/services/elo_service.py's _TIER_THRESHOLDS.
--
-- Like 0010_wine_tier.sql, production has real players, so this also
-- recomputes elo_level for every existing row — only scores >= 2100 move
-- (from 'vodka' to 'absinthe'), everyone else's band is unchanged.

alter table players drop constraint players_elo_level_check;
alter table players add constraint players_elo_level_check
    check (elo_level in ('milk', 'beer', 'highball', 'wine', 'soju', 'whisky', 'vodka', 'absinthe'));

update players set elo_level = case
    when elo_score < 900 then 'milk'
    when elo_score < 1100 then 'beer'
    when elo_score < 1300 then 'highball'
    when elo_score < 1500 then 'wine'
    when elo_score < 1700 then 'soju'
    when elo_score < 1900 then 'whisky'
    when elo_score < 2100 then 'vodka'
    else 'absinthe'
end;
