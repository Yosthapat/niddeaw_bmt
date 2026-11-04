-- Club credit: a member tops up (pays 950, gets 1,000 credits) and spends
-- the credit on court fees and shuttles (the night's bill) — not in the
-- shop. 1 credit = 1 baht.
--
--   credit_packages  what can be bought, set by the admin
--   player_credits   each member's balance — the one number a spend checks,
--                    and it can never go below zero
--   credit_topups    a top-up from LINE: the package, the slip, the
--                    admin's decision
--   credit_ledger    every change to a balance, with what it was for and
--                    the balance after it, so any balance can be traced
--
-- A balance is changed with a compare-and-swap (UPDATE ... WHERE balance =
-- <what was read>), the same way shop stock is taken, so two spends at
-- the same moment can't both use the same credit.
--
-- Run once, after 0035_expense_shop_cost.sql.

create table credit_packages (
    id uuid primary key default gen_random_uuid(),
    credits integer not null check (credits between 1 and 100000),
    -- What the member pays. Never more than the credit it buys.
    price numeric(10, 2) not null check (price > 0 and price <= credits),
    is_active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

insert into credit_packages (credits, price, sort_order) values
    (1000, 950, 0),
    (5000, 4500, 1);

create table player_credits (
    player_id uuid primary key references players (id),
    balance integer not null default 0 check (balance >= 0),
    updated_at timestamptz not null default now()
);

create table credit_topups (
    id uuid primary key default gen_random_uuid(),
    player_id uuid not null references players (id),
    -- Copied from the package, so a package changed later doesn't change
    -- what this member bought.
    credits integer not null check (credits > 0),
    price numeric(10, 2) not null check (price > 0),
    slip_url text,
    slip_sent_at timestamptz,
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected')),
    -- Why a slip was refused, shown to the member in LINE.
    note text check (note is null or char_length(note) <= 300),
    decided_at timestamptz,
    created_at timestamptz not null default now()
);

-- One top-up waiting per member at a time.
create unique index uq_credit_topups_pending on credit_topups (player_id) where status = 'pending';
create index idx_credit_topups_status on credit_topups (status, created_at);

create table credit_ledger (
    id uuid primary key default gen_random_uuid(),
    player_id uuid not null references players (id),
    delta integer not null check (delta <> 0),
    balance_after integer not null check (balance_after >= 0),
    kind text not null check (kind in ('topup', 'bill', 'refund', 'adjust')),
    -- Baht that actually changed hands with it: received for a top-up (or
    -- cash an admin took at the court), paid back for a refund. Null when
    -- no money moved — spending credit moves none.
    cash numeric(10, 2) check (cash is null or cash >= 0),
    -- The top-up, bill or order it was for.
    ref_id uuid,
    note text check (note is null or char_length(note) <= 300),
    admin_id uuid references admins (id) on delete set null,
    created_at timestamptz not null default now()
);

create index idx_credit_ledger_player on credit_ledger (player_id, created_at desc);
create index idx_credit_ledger_kind on credit_ledger (kind, created_at);

alter table credit_packages enable row level security;
alter table player_credits enable row level security;
alter table credit_topups enable row level security;
alter table credit_ledger enable row level security;
