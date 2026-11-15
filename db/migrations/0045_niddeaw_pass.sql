-- Niddeaw Pass: a monthly pass a member buys with credit.
--
-- While a pass runs, its holder:
--   * is paired onto the side with the better odds (52% or more) when the
--     suggestion can manage it;
--   * may name up to two members a night not to be partnered with (they can
--     still meet across the net, and are never told);
--   * earns 15% more season points for a win. ELO itself is not touched:
--     season points are worked out from the results, so nothing is stored
--     for them here.
-- Only a member holding a pink or black credit card (a 1,000 pack or more
-- bought through LINE, credit not yet spent) can buy one.

alter table credit_ledger drop constraint if exists credit_ledger_kind_check;
alter table credit_ledger add constraint credit_ledger_kind_check
    check (kind in ('topup', 'bill', 'refund', 'adjust', 'pass'));

create table passes (
    id uuid primary key default gen_random_uuid(),
    player_id uuid not null references players (id) on delete cascade,
    starts_at timestamptz not null default now(),
    ends_at timestamptz not null,
    credits integer not null check (credits >= 0),
    created_at timestamptz not null default now(),
    constraint pass_ends_after_start check (ends_at > starts_at)
);
create index idx_passes_player on passes (player_id, ends_at);

create table pass_blocks (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    player_id uuid not null references players (id) on delete cascade,
    blocked_id uuid not null references players (id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (session_id, player_id, blocked_id),
    constraint pass_block_not_self check (player_id <> blocked_id)
);
create index idx_pass_blocks_session on pass_blocks (session_id);

alter table club_settings add column pass_price integer not null default 249
    check (pass_price between 1 and 100000);

alter table passes enable row level security;
alter table pass_blocks enable row level security;
