-- What the QR on each transfer slip said, so a slip used twice is caught.
--
-- Every Thai bank slip carries a small QR holding the sending bank and the
-- transfer's own reference. When a member attaches a slip (a night's bill,
-- a credit top-up, a shop order) the server reads it and keeps one row per
-- thing paid for: sending a new slip for the same thing replaces the row.
-- The admin's screens then say, per slip, whether that reference has been
-- seen on anything else ("ซ้ำ"), whether there was no QR to read at all, or
-- that it is new. Nothing here approves or refuses a payment by itself.

create table slip_checks (
    id uuid primary key default gen_random_uuid(),
    kind text not null check (kind in ('bill', 'topup', 'order')),
    target_id uuid not null,
    slip_url text not null,
    qr_found boolean not null default false,
    qr_ref text check (qr_ref is null or length(qr_ref) between 4 and 64),
    bank_code text check (bank_code is null or bank_code ~ '^[0-9]{3}$'),
    created_at timestamptz not null default now(),
    unique (kind, target_id)
);

create index idx_slip_checks_ref on slip_checks (qr_ref) where qr_ref is not null;

alter table slip_checks enable row level security;
