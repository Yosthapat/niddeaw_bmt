-- Records the exact elo delta applied to each team when a match result is
-- submitted (matchmaking.py submit_result), so deleting the match's session
-- can undo the effect on player elo_score/games/wins/draws/losses exactly
-- instead of leaving it permanently applied (see sessions.py delete_session).

alter table matches add column elo_delta_team1 integer;
alter table matches add column elo_delta_team2 integer;
