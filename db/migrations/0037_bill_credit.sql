-- Paying a night's bill with club credit (0036). credit_used is how much
-- of the bill credit has paid, in whole credits (1 credit = 1 baht): all of
-- it when the member had enough, or part of it with the rest transferred.
--
-- The dues money counted for a bill is its amount less credit_used — the
-- baht behind that credit was already counted when the top-up came in.
--
-- Run once, after 0036_credit.sql.

alter table billings
    add column credit_used integer not null default 0 check (credit_used >= 0);
