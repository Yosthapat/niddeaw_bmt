-- Paying your own bill from LINE: the member transfers, attaches the slip,
-- and an admin checks it against the account and marks the bill paid.
--
-- slip_url is the slip they attached (a JPEG in the shop bucket, like the
-- shop's order slips). A bill with a slip and still unpaid is "waiting for
-- the admin". If the admin refuses the slip it is removed and
-- slip_rejected_at says so, so the member is asked for a new one rather
-- than left wondering.

alter table billings
    add column slip_url text check (slip_url is null or slip_url ~ '^https?://'),
    add column slip_sent_at timestamptz,
    add column slip_rejected_at timestamptz;
