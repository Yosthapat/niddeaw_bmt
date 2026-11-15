-- NIDDEAW CUP, phase 2: drawing the groups and the day's match list.
-- See docs/tournament-spec.md §3–4.
--
-- Groups are drawn by lot, level by level, from the confirmed teams. The
-- match list numbers every match of the day across all levels: the group
-- matches with their teams, the knockout matches as slots ("A1", "U3",
-- "W12" = the winner of match 12) that phase 3 fills in as results come.
-- Nothing is shown to players until an admin publishes it.

alter table tournaments
    -- When the first match starts on starts_on (club time, Asia/Bangkok).
    add column day_start time not null default '09:00',
    add column group_minutes integer not null default 20 check (group_minutes between 5 and 120),
    add column ko_minutes integer not null default 30 check (ko_minutes between 5 and 120),
    -- The least time a team gets between two of its matches.
    add column rest_minutes integer not null default 10 check (rest_minutes between 0 and 120),
    add column schedule_published_at timestamptz;

alter table tournament_teams
    add column group_label text check (group_label is null or group_label ~ '^[A-H]$'),
    add column group_pos integer check (group_pos is null or group_pos between 1 and 4);

-- One team per place in a group.
create unique index uq_tournament_group_place on tournament_teams (level_id, group_label, group_pos)
    where group_label is not null and status not in ('cancelled', 'withdrawn');

create table tournament_matches (
    id uuid primary key default gen_random_uuid(),
    tournament_id uuid not null references tournaments (id) on delete cascade,
    level_id uuid not null references tournament_levels (id) on delete cascade,
    match_no integer not null check (match_no > 0),
    stage text not null check (stage in ('group', 'ko')),
    bracket text check (bracket is null or bracket in ('upper', 'lower')),
    -- Group stage: 1–3. Knockout: how many teams the round starts with (16, 8, 4, 2).
    round integer not null check (round > 0),
    group_label text check (group_label is null or group_label ~ '^[A-H]$'),
    -- Who plays: a group place ("A1"), a seed ("U3" / "L2"), or a winner ("W12").
    slot_a text not null check (slot_a ~ '^([A-H][1-4]|[UL][0-9]{1,2}|W[0-9]{1,4})$'),
    slot_b text not null check (slot_b ~ '^([A-H][1-4]|[UL][0-9]{1,2}|W[0-9]{1,4})$'),
    team_a uuid references tournament_teams (id) on delete set null,
    team_b uuid references tournament_teams (id) on delete set null,
    -- A planning estimate from the courts and the minutes per match.
    est_start timestamptz,
    created_at timestamptz not null default now(),
    unique (tournament_id, match_no)
);

create index idx_tournament_matches_level on tournament_matches (level_id, match_no);

alter table tournament_matches enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches it.
