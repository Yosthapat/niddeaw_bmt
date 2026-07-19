-- Core schema for นิดเดียว Badminton Club.
-- Apply via Supabase SQL editor or `supabase db execute` — no ORM migration
-- runner is used (see ISSUE_beerminton_webapp.md decisions log).

create extension if not exists pgcrypto;

create table admins (
    id uuid primary key default gen_random_uuid(),
    username text not null unique,
    password_hash text not null,
    role text not null default 'admin' check (role in ('admin')),
    created_at timestamptz not null default now()
);

create table players (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    nickname text,
    avatar_url text,
    elo_score integer not null default 1000,
    elo_level text not null default 'soju'
        check (elo_level in ('milk', 'soju', 'beer', 'highball', 'vodka')),
    phone text,
    line_id text,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table sessions (
    id uuid primary key default gen_random_uuid(),
    date date not null,
    location text not null,
    rate_per_hour numeric(10, 2) not null,
    status text not null default 'open' check (status in ('open', 'closed')),
    created_by uuid not null references admins (id),
    created_at timestamptz not null default now()
);

create table checkins (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    player_id uuid not null references players (id),
    checkin_time timestamptz not null default now(),
    checkout_time timestamptz,
    constraint checkout_after_checkin check (checkout_time is null or checkout_time > checkin_time),
    constraint uq_checkins_session_player unique (session_id, player_id)
);

create table matches (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    type text not null check (type in ('single', 'double')),
    team1_player_ids uuid[] not null,
    team2_player_ids uuid[] not null,
    sets jsonb,
    winner text check (winner in ('team1', 'team2', 'draw')),
    status text not null default 'in_progress' check (status in ('in_progress', 'completed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table billings (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    player_id uuid not null references players (id),
    hours_played numeric(6, 2) not null,
    amount_calc numeric(10, 2) not null,
    amount_adjusted numeric(10, 2),
    paid_status text not null default 'unpaid' check (paid_status in ('unpaid', 'paid')),
    promptpay_ref text,
    updated_at timestamptz not null default now(),
    constraint uq_billings_session_player unique (session_id, player_id)
);

create table club_settings (
    id integer primary key default 1 check (id = 1),
    promptpay_id text not null default '',
    promptpay_type text not null default 'phone'
        check (promptpay_type in ('phone', 'national_id', 'ewallet')),
    default_rate_per_hour numeric(10, 2) not null default 0
);

create table pairing_history (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    match_id uuid not null references matches (id) on delete cascade,
    player_a_id uuid not null references players (id),
    player_b_id uuid not null references players (id),
    relation text not null check (relation in ('teammate', 'opponent')),
    round_no integer not null,
    created_at timestamptz not null default now()
);
