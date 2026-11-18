-- Niddeaw Pass, off the court: what a holder gets in the shop and at the
-- tournament desk (backend app/services/pass_service.py).
--
-- Shop: 5% off a whole order (in stock and pre-order alike), and a name
-- printed on the back of a shirt for free. Both only when the holder
-- orders for themselves from the club's LINE page, which is how the shop
-- knows who they are.
--
-- Tournament: 5% off what the holder pays to enter.
--
-- Run once, after 0050. Nothing already written changes: every existing
-- order, line and entrant reads as "no pass discount, no name".

-- A product that can have a name printed on it, and what that costs per
-- piece. null: no printing for this product.
alter table products
    add column name_print_price numeric(10, 2)
        check (name_print_price is null or name_print_price >= 0);

-- The name to print on this line's pieces, and what printing cost per
-- piece when it was bought (0 for a pass holder). line_total is
-- (unit_price + print_price) × qty.
alter table shop_order_items
    add column print_name text
        check (print_name is null or char_length(btrim(print_name)) between 1 and 20),
    add column print_price numeric(10, 2) not null default 0
        check (print_price >= 0);

-- Baht taken off the order for its buyer's pass. total is the lines less
-- this.
alter table shop_orders
    add column pass_discount numeric(10, 2) not null default 0
        check (pass_discount >= 0);

-- Baht taken off this entrant's share for their pass: share is already
-- the lowered amount, share + pass_off what they would have paid.
alter table tournament_entrants
    add column pass_off integer not null default 0
        check (pass_off >= 0);
