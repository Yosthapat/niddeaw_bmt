-- A new expense category: ต้นทุนร้านค้า (shop_cost), what the club pays to
-- make or buy what its shop sells. It comes off the account's balance like
-- every other expense; the shop page also takes it (and shirts, jersey) off
-- the shop's sales to show what the shop made.
--
-- Run once, after 0034_bill_slips.sql.

alter table expenses drop constraint if exists expenses_category_check;
alter table expenses
    add constraint expenses_category_check
    check (category in ('court_fee', 'shuttlecock', 'jersey', 'shop_cost', 'dividend', 'other'));
