-- Switch billing from hourly-rate to per-game: each player pays a flat
-- court fee per session they attend, plus a flat shuttlecock cost per game
-- they actually played (not split between teammates/opponents).
--
-- Check-ins are unaffected — still needed for attendance tracking and the
-- matchmaking queue — they're just no longer used to compute money owed.

alter table sessions rename column rate_per_hour to court_fee_per_person;
alter table sessions add column shuttlecock_price_per_game numeric(10, 2) not null default 0;

alter table club_settings rename column default_rate_per_hour to default_court_fee_per_person;
alter table club_settings add column default_shuttlecock_price_per_game numeric(10, 2) not null default 0;

alter table billings drop column hours_played;
alter table billings add column game_count integer not null default 0;
