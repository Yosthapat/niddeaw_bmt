-- NIDDEAW CUP, phase 3: the day itself. See docs/tournament-spec.md §4.
--
-- A match is called to a court, played, and its result entered by a
-- tournament admin from the signed score sheet. Group results make the
-- standings; once a level's groups are done its knockout slots are filled,
-- and each knockout winner moves on. Shuttle coupons are counted from the
-- shuttles each match used; extra sets sold and coupons bought back are
-- tournament_money rows (extra_shuttles / coupon_refund) with a team_id.

alter table tournament_matches
    add column status text not null default 'scheduled'
        check (status in ('scheduled', 'on_court', 'done')),
    add column court integer check (court is null or court between 1 and 60),
    add column called_at timestamptz,
    -- How many times it has been called; the rules allow a walkover after two.
    add column call_count integer not null default 0 check (call_count >= 0),
    add column finished_at timestamptz,
    -- [[a, b], [a, b], ...] — each set's points, side a first.
    add column sets jsonb,
    add column winner text check (winner is null or winner in ('a', 'b', 'draw')),
    add column walkover boolean not null default false,
    -- Shuttles the match used: each side gives one coupon per shuttle.
    add column shuttles integer check (shuttles is null or shuttles between 0 and 20),
    add column result_by uuid references admins (id) on delete set null,
    add constraint tournament_matches_on_court_check check ((status = 'on_court') = (court is not null)),
    add constraint tournament_matches_done_check check ((status = 'done') = (winner is not null));

-- One match on a court at a time.
create unique index uq_tournament_court on tournament_matches (tournament_id, court)
    where status = 'on_court';
create index idx_tournament_matches_status on tournament_matches (tournament_id, status);
