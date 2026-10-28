-- Sponsors shown on the home page's logo band, managed from the admin
-- screen instead of a code change per sponsor.
--
-- logo_url is either a file the backend uploaded to the public `sponsors`
-- bucket (a white silhouette it made from whatever the sponsor sent), or,
-- for the five logos that were already on the site, the path of the file
-- shipped with the frontend. logo_width / logo_height are the image's real
-- pixel size, so the page can reserve the right shape before it loads.

create table sponsors (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(btrim(name)) between 1 and 120),
    href text check (href is null or href ~ '^https?://'),
    logo_url text not null,
    logo_width integer not null check (logo_width > 0),
    logo_height integer not null check (logo_height > 0),
    sort_order integer not null default 0,
    is_visible boolean not null default true,
    created_at timestamptz not null default now()
);

create index idx_sponsors_order on sponsors (sort_order, created_at);

alter table sponsors enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.

insert into storage.buckets (id, name, public)
values ('sponsors', 'sponsors', true)
on conflict (id) do nothing;

-- The five already on the band, in the order they ran.
insert into sponsors (name, href, logo_url, logo_width, logo_height, sort_order) values
    ('Wasteland', 'https://www.instagram.com/wastelandbkk', '/sponsors/wasteland-mono.png', 424, 104, 1),
    ('Match Mellow', 'https://www.instagram.com/match.mellowww', '/sponsors/match-mellow-mono.png', 323, 205, 2),
    ('Sawadee Natural Herbal Balm', 'https://www.instagram.com/sawadee_naturalherbalbalm', '/sponsors/sawadee-mono.png', 417, 350, 3),
    ('Umore Made', 'https://www.instagram.com/umore.made', '/sponsors/umore-made-mono.png', 449, 169, 4),
    ('The Players Club', 'https://www.instagram.com/theplayersclubthailand', '/sponsors/players-club-mono.png', 354, 388, 5);
