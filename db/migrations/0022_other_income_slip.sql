-- Payment slip photo for other_income entries (sponsor/investment payments),
-- same idea as expenses.receipt_url. Reuses the existing public `receipts`
-- storage bucket (0014_expenses.sql) rather than creating a new one — it's
-- already a generic "proof of a transaction" photo bucket, and income_id vs
-- expense_id UUIDs never collide on a filename.

alter table other_income add column slip_url text;
