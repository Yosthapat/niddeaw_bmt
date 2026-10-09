-- Match numbers for the UI.
--
-- Admins and members talk about "แมตช์ที่ 5" but a match's only identity was
-- a uuid, so there was no way to say which one you meant out loud or in a
-- screenshot. This gives every match a running number across the club's whole
-- history — not per session — counted oldest-first.
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
create view matches_numbered as
select
    m.*,
    row_number() over (order by m.created_at, m.id) as match_no
from matches m;
