-- NIDDEAW CUP, phase 1: who may run it, the event, its levels, the teams
-- that sign up, and the event's own money. See docs/tournament-spec.md.
--
-- A tournament is kept apart from the club on purpose: its own admins, its
-- own PromptPay account, its own income and expenses. Nothing here touches
-- billings, credit, expenses or other_income, so the club's money pages
-- never count a tournament's money.

-- Two separate rights. Every admin today keeps the club and gets no
-- tournament; admin_van and admin_mo run tournaments too.
alter table admins
    add column club_access boolean not null default true,
    add column tournament_access boolean not null default false,
    add constraint admins_some_access check (club_access or tournament_access);

update admins set tournament_access = true where username in ('admin_van', 'admin_mo');

-- Each side reads only its own entries in the activity log.
alter table admin_activity_log
    add column area text not null default 'club' check (area in ('club', 'tournament'));

create index idx_admin_activity_log_area on admin_activity_log (area, created_at desc);

-- A slip sent for a tournament entry is checked against every other slip,
-- the club's included, so one transfer can't pay for two things.
alter table slip_checks drop constraint slip_checks_kind_check;
alter table slip_checks
    add constraint slip_checks_kind_check check (kind in ('bill', 'topup', 'order', 'tournament'));

create table tournaments (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(btrim(name)) between 2 and 80),
    starts_on date not null,
    venue text not null default '' check (char_length(venue) <= 120),
    -- Per team, in baht. Each player pays half (the captain the odd baht).
    entry_fee integer not null default 1600 check (entry_fee between 0 and 100000),
    -- The first set of shuttle coupons, paid with the entry.
    shuttle_fee integer not null default 450 check (shuttle_fee between 0 and 100000),
    coupons_per_set integer not null default 6 check (coupons_per_set between 1 and 50),
    extra_set_price integer not null default 450 check (extra_set_price between 0 and 100000),
    coupon_refund_price integer not null default 70 check (coupon_refund_price between 0 and 10000),
    -- The event's own account, never the club's.
    promptpay_id text check (promptpay_id is null or promptpay_id ~ '^[0-9]{10,15}$'),
    promptpay_type text check (promptpay_type is null or promptpay_type in ('phone', 'national_id', 'ewallet')),
    account_name text check (account_name is null or char_length(account_name) <= 80),
    opens_at timestamptz,
    closes_at timestamptz not null,
    min_games integer not null default 3 check (min_games between 0 and 100),
    courts integer check (courts is null or courts between 1 and 60),
    status text not null default 'draft' check (status in ('draft', 'open', 'closed', 'running', 'done')),
    created_by uuid references admins (id) on delete set null,
    created_at timestamptz not null default now()
);

create table tournament_levels (
    id uuid primary key default gen_random_uuid(),
    tournament_id uuid not null references tournaments (id) on delete cascade,
    name text not null check (char_length(btrim(name)) between 1 and 40),
    -- [min_elo, max_elo): null min = no floor, null max = no ceiling.
    min_elo integer,
    max_elo integer,
    max_teams integer not null default 16 check (max_teams in (16, 24, 32)),
    -- 24 teams only: false = 16 up / 8 down, true = 8 up / 8 down / 8 out.
    cut_24 boolean not null default false,
    rules text not null default '' check (char_length(rules) <= 300),
    sort integer not null default 0,
    check (min_elo is null or max_elo is null or min_elo < max_elo)
);

create index idx_tournament_levels_tournament on tournament_levels (tournament_id, sort);

create table tournament_teams (
    id uuid primary key default gen_random_uuid(),
    tournament_id uuid not null references tournaments (id) on delete cascade,
    level_id uuid not null references tournament_levels (id),
    name text not null check (char_length(btrim(name)) between 2 and 40),
    status text not null default 'invited' check (
        status in ('invited', 'awaiting_payment', 'slip_review', 'confirmed', 'waitlist', 'cancelled', 'withdrawn')
    ),
    -- When an invite, or a wait to pay, runs out.
    expires_at timestamptz,
    invited_at timestamptz not null default now(),
    accepted_at timestamptz,
    -- Both slips sent and a place free: the place is theirs from here.
    seat_held_at timestamptz,
    waitlist_at timestamptz,
    confirmed_at timestamptz,
    ended_at timestamptz,
    -- Withdrawn by an admin who decided its fees are kept.
    no_refund boolean not null default false,
    created_by_admin uuid references admins (id) on delete set null,
    created_at timestamptz not null default now()
);

-- No two live teams in one level share a name (any case, outer spaces ignored).
create unique index uq_tournament_team_name on tournament_teams (level_id, lower(btrim(name)))
    where status not in ('cancelled', 'withdrawn');
create index idx_tournament_teams_tournament on tournament_teams (tournament_id, status);

-- One row per player per team: two to a team.
create table tournament_entrants (
    id uuid primary key default gen_random_uuid(),
    tournament_id uuid not null references tournaments (id) on delete cascade,
    team_id uuid not null references tournament_teams (id) on delete cascade,
    player_id uuid not null references players (id),
    role text not null check (role in ('captain', 'partner')),
    -- False once the team is cancelled or withdrawn, so the player can sign up again.
    active boolean not null default true,
    -- Filled in by the player themselves (the partner when they accept).
    -- Only admins and the player see them.
    first_name text check (first_name is null or char_length(first_name) between 1 and 60),
    last_name text check (last_name is null or char_length(last_name) between 1 and 60),
    phone text check (phone is null or phone ~ '^0[0-9]{8,9}$'),
    elo integer,
    share integer not null check (share >= 0),
    pay_status text not null default 'unpaid' check (pay_status in ('unpaid', 'slip_sent', 'paid', 'rejected', 'refunded')),
    paid_via text check (paid_via is null or paid_via in ('transfer', 'cash')),
    slip_url text,
    slip_sent_at timestamptz,
    paid_at timestamptz,
    checked_by uuid references admins (id) on delete set null,
    rejected_at timestamptz,
    refund_slip_url text,
    refunded_at timestamptz,
    created_at timestamptz not null default now(),
    unique (team_id, role)
);

-- One live team per player per tournament.
create unique index uq_tournament_entrant_player on tournament_entrants (tournament_id, player_id) where active;
create index idx_tournament_entrants_team on tournament_entrants (team_id);
create index idx_tournament_entrants_player on tournament_entrants (player_id);

-- The tournament's own income and expenses.
create table tournament_money (
    id uuid primary key default gen_random_uuid(),
    tournament_id uuid not null references tournaments (id) on delete cascade,
    direction text not null check (direction in ('income', 'expense')),
    category text not null check (
        category in (
            'entry_fee', 'extra_shuttles', 'sponsor', 'other_income',
            'court', 'shuttle', 'trophy', 'prize', 'staff', 'photo', 'refund', 'coupon_refund', 'other'
        )
    ),
    category_other text check (category_other is null or char_length(category_other) <= 60),
    amount numeric(10, 2) not null check (amount > 0),
    entry_date date not null,
    paid_by uuid references admins (id) on delete set null,
    -- Set when the row came from an entry (a fee received, a fee refunded)
    -- or a sale to a team; such rows are written by the system, not typed.
    entrant_id uuid references tournament_entrants (id) on delete set null,
    team_id uuid references tournament_teams (id) on delete set null,
    quantity integer check (quantity is null or quantity > 0),
    unit_price numeric(10, 2),
    paid_via text check (paid_via is null or paid_via in ('transfer', 'cash')),
    receipt_url text,
    note text check (note is null or char_length(note) <= 300),
    created_by uuid references admins (id) on delete set null,
    created_at timestamptz not null default now()
);

create index idx_tournament_money_tournament on tournament_money (tournament_id, entry_date desc);
-- A received fee is counted once.
create unique index uq_tournament_money_fee on tournament_money (entrant_id, category)
    where entrant_id is not null;

alter table tournaments enable row level security;
alter table tournament_levels enable row level security;
alter table tournament_teams enable row level security;
alter table tournament_entrants enable row level security;
alter table tournament_money enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches these.
