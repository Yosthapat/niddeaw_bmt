-- NIDDEAW CUP: team names may repeat in a level, and the knockout's first
-- round is drawn by lot.
--
-- A club can enter several teams under its own name (the draw keeps teams
-- of one name in different groups), so the one-name-per-level index goes.
--
-- Each knockout bracket's first round puts its seeded teams (the group
-- winners, in group order, A B C …) against opponents drawn by lot from the
-- rest, never from their own group. A drawn opponent's slot is "P1"…"P16"
-- (upper) or "Q1"…"Q16" (lower) until the groups are done and the draw made.

drop index if exists uq_tournament_team_name;

alter table tournament_matches drop constraint tournament_matches_slot_a_check;
alter table tournament_matches drop constraint tournament_matches_slot_b_check;
alter table tournament_matches
    add constraint tournament_matches_slot_a_check
        check (slot_a ~ '^([A-H][1-4]|[ULPQ][0-9]{1,2}|W[0-9]{1,4})$'),
    add constraint tournament_matches_slot_b_check
        check (slot_b ~ '^([A-H][1-4]|[ULPQ][0-9]{1,2}|W[0-9]{1,4})$');
