-- Tracks whether a logged expense has actually been settled/paid out yet
-- (e.g. a jersey order invoice gets logged when it arrives, then marked
-- paid once the club actually transfers the money) — separate from
-- `paid_by`, which just records which admin is on the hook for it.

alter table expenses
    add column is_paid boolean not null default false,
    add column paid_at timestamptz;
