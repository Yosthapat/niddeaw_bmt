-- Admin expense tracking: court fees, shuttlecocks, jerseys, and anything
-- else the club pays for, each with who paid and an optional receipt/slip
-- photo. Separate from `billings` (money members owe the club) — this is
-- money the club (via one of its 3 admins) pays out.

create table expenses (
    id uuid primary key default gen_random_uuid(),
    expense_date date not null,
    category text not null
        check (category in ('court_fee', 'shuttlecock', 'jersey', 'other')),
    -- Free-text label, required when category = 'other' (e.g. "ค่าน้ำ")
    -- and ignored otherwise — enforced in the API layer, not here, since
    -- checking "required iff X" needs a CASE, more hassle than it's worth
    -- for one optional column.
    category_other text,
    amount numeric(10, 2) not null check (amount > 0),
    paid_by uuid not null references admins (id),
    receipt_url text,
    note text,
    created_by uuid not null references admins (id),
    created_at timestamptz not null default now()
);

create index idx_expenses_date on expenses (expense_date desc);

alter table expenses enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.

-- Public read (receipt URLs load directly in admin <img> tags), writes only
-- through the backend's service-role key — mirrors 0005_storage_bucket.sql.
insert into storage.buckets (id, name, public)
values ('receipts', 'receipts', true)
on conflict (id) do nothing;
