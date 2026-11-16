-- Niddeaw Pass: how a member dresses their profile.
--
-- frame: the ring around their picture wherever it shows (profile, live
-- board, ranking). card: the face of their profile card.
--
-- gold, neon, crown and the foil card show while a pass runs. moon, king
-- and legend (frames) and diamond (card) are earned by holding the pass
-- 3, 6 and 12 months back to back; once earned they are kept for good,
-- pass or no pass. Which of these a member has earned is worked out from
-- `passes`, so nothing about it is stored here.

create table pass_styles (
    player_id uuid primary key references players (id) on delete cascade,
    frame text check (frame in ('gold', 'neon', 'crown', 'moon', 'king', 'legend')),
    card text check (card in ('foil', 'diamond')),
    updated_at timestamptz not null default now()
);

alter table pass_styles enable row level security;
