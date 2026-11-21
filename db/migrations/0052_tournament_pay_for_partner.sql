-- NIDDEAW CUP: one player may pay for the whole team.
--
-- Until now each player transferred their own share. Now either player,
-- once the partner has accepted, may pay both shares with one transfer.
-- The partner's row then carries the same slip and points at whoever paid
-- (covered_by): the slip is checked once for both, a rejected slip puts the
-- partner back to unpaid, and a refund for the team goes back to the payer
-- in one amount (backend app/services/tournament_service.py).
--
-- Each share stays as it was (a Niddeaw Pass holder's share keeps its own
-- discount), so the tournament's income per player is unchanged.
--
-- Run once, after 0051. Every existing entrant reads as "paid for
-- themselves".

alter table tournament_entrants
    add column covered_by uuid references tournament_entrants (id) on delete set null,
    add constraint tournament_entrants_not_self_covered check (covered_by is null or covered_by <> id);

notify pgrst, 'reload schema';
