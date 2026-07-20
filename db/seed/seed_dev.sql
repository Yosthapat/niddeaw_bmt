-- Local dev fixtures only — never run against the real production Supabase
-- project. Gives you a handful of players, an open session with checkins,
-- and one completed match so the frontend has something to render.

-- Admin login: username "admin", password "changeme123" (bcrypt hash below,
-- verified against the app's actual hash_password/verify_password).
-- Generate your own via: pdm run python3 -c "from app.security import hash_password; print(hash_password('changeme123'))"
insert into admins (id, username, password_hash, role) values
    ('00000000-0000-0000-0000-000000000001', 'admin',
     '$2b$12$7dG3iWtf3c.L5bvcxiW5ceG9ZB8mGPk/b.A4542QxgRViQKj87NPa',
     'admin');

insert into players (id, nickname, elo_score, elo_level) values
    ('00000000-0000-0000-0000-000000000101', 'Chai', 1000, 'soju'),
    ('00000000-0000-0000-0000-000000000102', 'Su', 1150, 'beer'),
    ('00000000-0000-0000-0000-000000000103', 'Nan', 1350, 'whisky'),
    ('00000000-0000-0000-0000-000000000104', 'Pim', 1550, 'highball');

insert into sessions (id, date, location, court_fee_per_person, shuttlecock_price_per_game, status, created_by) values
    ('00000000-0000-0000-0000-000000000201', current_date, 'สนามแบดหลังบ้าน', 80.00, 29.00, 'open',
     '00000000-0000-0000-0000-000000000001');

insert into checkins (session_id, player_id, checkin_time) values
    ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000101', now() - interval '1 hour'),
    ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000102', now() - interval '1 hour'),
    ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000103', now() - interval '45 minutes'),
    ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000104', now() - interval '45 minutes');

insert into matches (
    id, session_id, type, team1_player_ids, team2_player_ids, sets, winner, status, created_at, updated_at
) values (
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000201',
    'double',
    array['00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000102']::uuid[],
    array['00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000104']::uuid[],
    '[[21,18],[19,21],[21,17]]'::jsonb,
    'team1',
    'completed',
    now() - interval '40 minutes',
    now() - interval '20 minutes'
);
