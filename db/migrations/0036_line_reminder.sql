-- The Friday check-in reminder sent through the club's LINE OA
-- (backend/app/services/line_reminder.py): when it went out for a night
-- and to how many people. The time is also the guard that makes it go out
-- once per night, however often the scheduled job knocks.
--
-- Run once, after 0035_expense_shop_cost.sql.

alter table sessions
    add column line_reminder_sent_at timestamptz,
    add column line_reminder_count integer check (line_reminder_count is null or line_reminder_count >= 0);
