-- NIDDEAW CUP: teams checked in on the day.
--
-- The desk marks each team as it arrives. Once anyone has been checked in,
-- the game-day screen only offers matches whose two teams are both here
-- (tournament_play.ready); before that, check-in is simply not in use.

alter table tournament_teams add column arrived_at timestamptz;
