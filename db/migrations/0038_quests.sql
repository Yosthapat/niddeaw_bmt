-- Quests and badges: members earn medals for what they do at the club
-- (win streaks, nights attended, beating a stronger team, ...). The
-- medals are worked out from the matches, check-ins and nights themselves
-- (backend/app/services/quest_service.py); this table only remembers what
-- was earned, when, and whether the member has seen it yet, for the LINE
-- pop-up and the "latest in the club" feed.
--
--   quest_settings  one row: the day counting started (nothing before it
--                   counts) and the monthly quest's target
--   player_badges   one row per medal a member holds: quest + level
--
-- Run once, after 0037_bill_credit.sql. Counting starts the day this runs
-- (Bangkok time); the admin can move the date on the settings page.

create table quest_settings (
    id smallint primary key default 1 check (id = 1),
    start_date date not null default ((now() at time zone 'Asia/Bangkok')::date),
    monthly_target integer not null default 20 check (monthly_target between 1 and 200),
    -- What the medals were last worked out from; when it changes, they are
    -- worked out again.
    synced_key text
);

insert into quest_settings (id) values (1);

create table player_badges (
    player_id uuid not null references players (id) on delete cascade,
    -- fire, regular, ..., podium, monthly:2026-12, secret_opener, ...
    badge text not null check (badge ~ '^[a-z0-9_:-]{1,40}$'),
    level smallint not null check (level between 1 and 10),
    earned_at timestamptz not null,
    seen_at timestamptz,
    created_at timestamptz not null default now(),
    primary key (player_id, badge, level)
);

create index idx_player_badges_earned on player_badges (earned_at desc);

alter table quest_settings enable row level security;
alter table player_badges enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches these.

-- The backend's key needs these spelled out (0036 needed the same).
grant select, insert, update, delete on quest_settings, player_badges to service_role;

notify pgrst, 'reload schema';
