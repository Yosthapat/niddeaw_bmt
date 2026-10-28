-- The club shop: products the admin adds, orders members place from the
-- site (pick their own name, pay by PromptPay, attach the slip), and the
-- stock those orders draw down.
--
-- Two ways of selling, per product:
--   'stock'    — the goods exist; each order takes from product_stock, and
--                a size at 0 shows as sold out.
--   'preorder' — nothing exists yet; orders are collected until
--                preorder_closes_on, then the admin orders the total made.

create table products (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(btrim(name)) between 1 and 120),
    description text check (description is null or char_length(description) <= 1000),
    price numeric(10, 2) not null check (price > 0 and price <= 1000000),
    sale_type text not null check (sale_type in ('stock', 'preorder')),
    -- Empty means "one size": a sticker set, a keychain.
    sizes text[] not null default '{}',
    preorder_closes_on date,
    preorder_delivers_on date,
    -- The first is the cover.
    image_urls text[] not null default '{}',
    is_active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now(),
    check (sale_type <> 'preorder' or preorder_closes_on is not null)
);

-- One row per size (size '' for a one-size product). Its own table rather
-- than a json column so an order can take one unit with a single
-- conditional UPDATE ... WHERE qty = <what it read>: two members buying the
-- last shirt at the same moment cannot both get it.
create table product_stock (
    product_id uuid not null references products (id) on delete cascade,
    size text not null default '',
    qty integer not null check (qty >= 0),
    primary key (product_id, size)
);

create table shop_orders (
    id uuid primary key default gen_random_uuid(),
    -- What people say out loud and what the admin searches for: S-0012.
    order_no bigint generated always as identity,
    player_id uuid not null references players (id),
    -- Kept if the product is later deleted; the name and price are copied
    -- so an old order still says what was bought and for how much.
    product_id uuid references products (id) on delete set null,
    product_name text not null,
    sale_type text not null check (sale_type in ('stock', 'preorder')),
    size text not null default '',
    qty integer not null check (qty between 1 and 10),
    unit_price numeric(10, 2) not null check (unit_price > 0),
    total numeric(10, 2) not null check (total > 0),
    slip_url text not null,
    status text not null default 'pending'
        check (status in ('pending', 'confirmed', 'delivered', 'rejected')),
    -- Why a slip was refused, shown to the member on their profile.
    note text check (note is null or char_length(note) <= 300),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_shop_orders_status on shop_orders (status, created_at desc);
create index idx_shop_orders_player on shop_orders (player_id, created_at desc);
create index idx_products_order on products (sort_order, created_at);

alter table products enable row level security;
alter table product_stock enable row level security;
alter table shop_orders enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches these.

-- Product photos and payment slips. Public like `receipts`: every object
-- name carries a random part, so a URL cannot be guessed.
insert into storage.buckets (id, name, public)
values ('shop', 'shop', true)
on conflict (id) do nothing;
