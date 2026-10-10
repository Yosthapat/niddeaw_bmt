-- Match numbers for the UI.
--
-- Admins and members talk about "แมตช์ที่ 5" but a match's only identity was
-- a uuid, so there was no way to say which one you meant out loud or in a
-- screenshot. This gives every match a running number across the club's whole
-- history — not per session — counted oldest-first. Matches already played
-- are numbered too: the number is computed from the rows that exist, so no
-- backfill and no change to the matches table itself.
--
-- A view, not a stored column, because the number is defined as a *rank*: if
-- a match is removed the ones after it move up to close the gap, which is the
-- behaviour the club asked for. A stored column would freeze the number at
-- insert time and leave holes instead.
--
-- Ordered by (created_at, id), not created_at alone: created_at is not unique
-- and two matches confirmed in the same transaction share it to the
-- microsecond, which would let their two numbers swap between one request and
-- the next. The uuid tie-break is arbitrary but it is stable.
--
-- Reads that need the number select from this view; every write still goes to
-- the matches table itself.
--
-- security_invoker, and the revoke below, keep the deny-by-default posture
-- 0004 set up. A view runs as its *owner* unless told otherwise, so a plain
-- view over an RLS-protected table hands out every row to whoever can select
-- it — verified on Postgres 16: anon reads 0 rows from `matches` but all of
-- them through a plain view, and 0 again through this one. Supabase also
-- grants select on new public objects to anon and authenticated by default,
-- so that grant is taken back explicitly: only the backend's service-role key
-- reads this, same as every other table.
create view matches_numbered
with (security_invoker = true) as
select
    m.*,
    row_number() over (order by m.created_at, m.id) as match_no
from matches m;

revoke all on matches_numbered from anon, authenticated;
grant select on matches_numbered to service_role;

-- Already ran an earlier draft of this file, the one that was just
-- `create view matches_numbered as select ...` with nothing after it? The
-- view is there but outside the RLS fence. These three statements bring it
-- up to the state above without dropping it (verified on Postgres 16:
-- before them anon reads all 5 rows through the view, after them anon is
-- denied and service_role still reads all 5):
--
--     alter view matches_numbered set (security_invoker = true);
--     revoke all on matches_numbered from anon, authenticated;
--     grant select on matches_numbered to service_role;
