-- The shop grows a cart: one order, one slip, several lines — a shirt in M
-- and another in XL, and a cap, paid in one transfer. And a size can cost
-- more than another (XL +20, 2XL +40).
--
-- Run once, after 0027_shop.sql. Orders already placed keep their line:
-- each becomes an order with a single item.

-- Price per size where it differs from the product's own price. A size
-- missing from the map costs `price`.
alter table products
    add column size_prices jsonb not null default '{}'::jsonb
        check (jsonb_typeof(size_prices) = 'object');

create table shop_order_items (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references shop_orders (id) on delete cascade,
    -- Kept if the product is later deleted; the name and the price are
    -- copied so an old order still says what was bought and for how much.
    product_id uuid references products (id) on delete set null,
    product_name text not null,
    sale_type text not null check (sale_type in ('stock', 'preorder')),
    size text not null default '',
    qty integer not null check (qty between 1 and 10),
    unit_price numeric(10, 2) not null check (unit_price > 0),
    line_total numeric(10, 2) not null check (line_total > 0),
    created_at timestamptz not null default now()
);

create index idx_shop_order_items_order on shop_order_items (order_id);
create index idx_shop_order_items_product on shop_order_items (product_id);

insert into shop_order_items (order_id, product_id, product_name, sale_type, size, qty, unit_price, line_total, created_at)
select id, product_id, product_name, sale_type, size, qty, unit_price, total, created_at
from shop_orders;

-- What was bought now lives on the items; the order keeps who, how much
-- in all, the slip and where it is.
alter table shop_orders
    drop column product_id,
    drop column product_name,
    drop column sale_type,
    drop column size,
    drop column qty,
    drop column unit_price;

alter table shop_order_items enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches it.
