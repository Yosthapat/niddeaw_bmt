-- A new expense category: เงินปันผล (dividend), money the club pays out
-- to its members from what it has saved. It counts as money out like every
-- other expense.
--
-- Run once, after 0029_shop_guests.sql. The check came from 0014 as an
-- inline column check, which Postgres named expenses_category_check.

alter table expenses drop constraint if exists expenses_category_check;
alter table expenses
    add constraint expenses_category_check
    check (category in ('court_fee', 'shuttlecock', 'jersey', 'dividend', 'other'));
