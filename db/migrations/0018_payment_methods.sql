-- Lets the club choose how it collects payment, beyond just PromptPay:
-- PromptPay (amount auto-filled — the only method that supports this,
-- since it's the only interbank QR standard open to third-party
-- generation), a plain bank account shown as text, a QR generated from
-- that bank account's text (no amount — not a real payment-QR standard,
-- just a scan-to-copy convenience), or an admin-uploaded QR image (e.g. a
-- bank's own "Mae Manee"-style merchant QR) shown as-is.

alter table club_settings
    add column payment_method text not null default 'promptpay'
        check (payment_method in ('promptpay', 'bank_account', 'bank_account_qr', 'uploaded_qr')),
    add column bank_name text,
    add column bank_account_number text,
    add column bank_account_name text,
    add column uploaded_qr_url text;

-- Public read (uploaded QR loads directly in an <img> tag), writes only
-- through the backend's service-role key — mirrors 0005_storage_bucket.sql.
insert into storage.buckets (id, name, public)
values ('payment-qr', 'payment-qr', true)
on conflict (id) do nothing;
