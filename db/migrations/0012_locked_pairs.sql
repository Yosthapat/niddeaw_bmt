-- Per-session "lock pair" — admin can pin two checked-in players as
-- permanent teammates for the rest of THIS session only (e.g. two friends
-- who came together today), without it sticking to their profile forever
-- (since who they come with can change day to day). The matchmaking
-- suggestion algorithm keeps a locked pair on the same team every round,
-- automatically finding opponents for them, until admin unlocks or the
-- session ends (cascade-deleted with it).

create table locked_pairs (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references sessions (id) on delete cascade,
    player_a_id uuid not null references players (id),
    player_b_id uuid not null references players (id),
    created_at timestamptz not null default now(),
    constraint locked_pairs_distinct_players check (player_a_id <> player_b_id)
);

create index locked_pairs_session_id_idx on locked_pairs (session_id);
