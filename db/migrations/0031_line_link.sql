-- Members link their LINE account to their name in the club, so LINE can
-- stand in for them later: checking in at the court by scanning a QR,
-- seeing their own bill.
--
-- line_user_id is LINE's own id for the person (U + 32 hex), the `sub` of
-- the ID token LINE Login hands back. It is per LINE provider, which is why
-- the LINE Login channel must sit under the same provider as the club's
-- Official Account. It is not the "LINE ID" handle players.line_id holds,
-- which a person picks and can change. line_name is their LINE display name
-- when the link was approved, so the admin can tell who is linked.
--
-- A link is never made by the member alone: they pick their name, which
-- files a request, and an admin approves it. Otherwise anyone could claim
-- anyone and check in as them.

alter table players
    add column line_user_id text check (line_user_id is null or line_user_id ~ '^U[0-9a-f]{32}$'),
    add column line_name text check (line_name is null or char_length(line_name) <= 100);

create unique index uq_players_line_user_id on players (line_user_id) where line_user_id is not null;

create table line_link_requests (
    id uuid primary key default gen_random_uuid(),
    line_user_id text not null check (line_user_id ~ '^U[0-9a-f]{32}$'),
    line_name text not null check (char_length(line_name) between 1 and 100),
    line_picture text check (line_picture is null or line_picture ~ '^https://'),
    player_id uuid not null references players (id) on delete cascade,
    status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    created_at timestamptz not null default now(),
    decided_at timestamptz,
    decided_by uuid references admins (id)
);

-- One open request per LINE account: picking again replaces it.
create unique index uq_line_link_requests_pending
    on line_link_requests (line_user_id) where status = 'pending';
create index idx_line_link_requests_status on line_link_requests (status, created_at);

alter table line_link_requests enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.
