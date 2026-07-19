-- Enable Row Level Security on every table with ZERO policies defined.
--
-- The backend only ever connects using the Supabase service-role key, which
-- bypasses RLS entirely — so this does not affect the app's normal
-- operation. What it buys us is defense-in-depth: since no policies grant
-- anon/authenticated roles any access, even a leaked anon key or a future
-- frontend regression that accidentally imports the Supabase JS client
-- would be able to read or write NOTHING. Only the service-role key
-- (backend-only, never shipped to the browser) can touch this data.

alter table admins enable row level security;
alter table players enable row level security;
alter table sessions enable row level security;
alter table checkins enable row level security;
alter table matches enable row level security;
alter table billings enable row level security;
alter table club_settings enable row level security;
alter table pairing_history enable row level security;

-- No policies created — deny-by-default for anon/authenticated roles.
-- If a future feature ever needs the frontend to read public data directly
-- from Supabase (bypassing the FastAPI backend), an explicit read-only
-- policy could be added here, e.g.:
--   create policy "public read players" on players for select using (true);
-- ...but per the architecture decision in ISSUE_beerminton_webapp.md, the
-- frontend must never talk to Supabase directly, so none are added.
