-- Signing up through LINE: someone who is not in the club yet fills in
-- their own nickname, hand, handles and photo on the /line page. That is an
-- application, not a member: an admin accepts it (and sets the starting
-- tier), which is when the player row is created, already linked to the
-- LINE account that applied. Until then they are nobody in the club — no
-- member code, nothing on the ranking.
--
-- photo_url is an avatar-sized JPEG the backend already stored in the
-- avatars bucket (their own photo, or their LINE picture), so accepting the
-- application only has to point the new player at it.

create table line_join_requests (
    id uuid primary key default gen_random_uuid(),
    line_user_id text not null check (line_user_id ~ '^U[0-9a-f]{32}$'),
    line_name text not null check (char_length(line_name) between 1 and 100),
    nickname text not null check (char_length(nickname) between 1 and 40),
    dominant_hand text check (dominant_hand in ('left', 'right')),
    instagram text check (instagram is null or char_length(instagram) <= 100),
    tiktok text check (tiktok is null or char_length(tiktok) <= 100),
    quote text check (quote is null or char_length(quote) <= 500),
    photo_url text check (photo_url is null or photo_url ~ '^https?://'),
    status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    player_id uuid references players (id) on delete set null,
    created_at timestamptz not null default now(),
    decided_at timestamptz,
    decided_by uuid references admins (id)
);

-- One open application per LINE account: sending again replaces it.
create unique index uq_line_join_requests_pending
    on line_join_requests (line_user_id) where status = 'pending';
create index idx_line_join_requests_status on line_join_requests (status, created_at);

alter table line_join_requests enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.
