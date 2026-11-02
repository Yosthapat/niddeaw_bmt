-- Someone from outside the club can order from the shop: no member to pick,
-- so the order keeps the name and phone they typed instead. They collect at
-- the court like everyone else; the phone is for the admin only.
--
-- Run once, after 0028_shop_cart.sql. Orders already placed are members'
-- and stay as they are.

alter table shop_orders alter column player_id drop not null;

alter table shop_orders
    add column guest_name text
        check (guest_name is null or char_length(btrim(guest_name)) between 1 and 80),
    add column guest_phone text
        check (guest_phone is null or guest_phone ~ '^0[0-9]{8,9}$');

-- Every order is a member's or a guest's — never both, never neither.
alter table shop_orders
    add constraint shop_orders_buyer check (
        (player_id is not null and guest_name is null and guest_phone is null)
        or (player_id is null and guest_name is not null and guest_phone is not null)
    );
