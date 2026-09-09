-- Non-billing revenue: sponsor payments, investment injections, or any
-- other money coming into the club that isn't a member's court-fee bill.
-- Separate from `billings` (money members owe for playing) so the Revenue
-- page can show the full picture without conflating the two.

create table other_income (
    id uuid primary key default gen_random_uuid(),
    income_date date not null,
    source text not null
        check (source in ('sponsor', 'investment', 'other')),
    -- Free-text label naming who it's from (e.g. "Wasteland", "ผู้ร่วมทุน A") —
    -- required for every source, since even 'other' needs some description.
    source_name text not null,
    amount numeric(10, 2) not null check (amount > 0),
    note text,
    created_by uuid not null references admins (id),
    created_at timestamptz not null default now()
);

create index idx_other_income_date on other_income (income_date desc);

alter table other_income enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.
