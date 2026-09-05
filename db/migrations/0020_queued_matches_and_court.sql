-- "Queued" matches: an admin can pre-build the next pairing — including
-- players who are still mid-match — so there's no dead time between rounds
-- when there aren't enough free (not currently playing) checked-in players
-- to draw a full group from. A queued match is promoted to in_progress only
-- by an explicit admin action (see /matches/{id}/start in the matchmaking
-- router), never automatically, so the admin stays in control of exactly
-- when a court is actually free.
--
-- `court` is a free-text label (e.g. "1", "คอร์ตริมสุด") rather than a fixed
-- enum, since courts-per-venue varies by location.

alter table matches drop constraint matches_status_check;
alter table matches add constraint matches_status_check
    check (status in ('queued', 'in_progress', 'completed'));

alter table matches add column court text;
