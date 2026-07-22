-- Denormalize per-player games/wins/draws/losses onto the players table,
-- incrementally updated in submit_result (see
-- backend/app/routers/admin/matchmaking.py) instead of recomputed from a
-- full scan of every completed match on every read. Same pattern already
-- used for elo_score/elo_level. Points/avg_points/score_percent stay
-- derived in Python (stats_service.PlayerRecord) — trivial from these four.
--
-- Read paths updated to use these columns directly: public players list,
-- player profile, match detail, ranking (all-time), hall of fame.
-- Ranking's period=year still scans matches live (bounded to one year's
-- worth, not the whole club history) since year-bucketed denormalization
-- isn't worth the complexity yet.

alter table players add column games integer not null default 0;
alter table players add column wins integer not null default 0;
alter table players add column draws integer not null default 0;
alter table players add column losses integer not null default 0;

-- Backfill from whatever completed matches already exist.
with match_players as (
    select id as match_id, winner, unnest(team1_player_ids) as player_id, 'team1' as side
    from matches where status = 'completed'
    union all
    select id as match_id, winner, unnest(team2_player_ids) as player_id, 'team2' as side
    from matches where status = 'completed'
),
aggregated as (
    select
        player_id,
        count(*) as games,
        count(*) filter (where winner = side) as wins,
        count(*) filter (where winner = 'draw') as draws,
        count(*) filter (where winner is not null and winner <> side and winner <> 'draw') as losses
    from match_players
    group by player_id
)
update players p
set games = a.games, wins = a.wins, draws = a.draws, losses = a.losses
from aggregated a
where p.id = a.player_id;
