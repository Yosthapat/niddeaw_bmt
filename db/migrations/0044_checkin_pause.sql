-- A member resting between games without going home.
--
-- Some members can only manage a game, then need a break, but are not done
-- for the night. Checking them out would bill them early and drop them off
-- the night; instead the admin pauses them: while paused_at is set they are
-- left out of the suggested pairings, and the admin presses "กลับมาเล่น"
-- to put them back in the queue. Billing is unchanged — they are still in.

alter table checkins add column paused_at timestamptz;
