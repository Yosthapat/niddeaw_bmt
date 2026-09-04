-- Records every write (POST/PATCH/PUT/DELETE) an admin makes against
-- /api/admin/* — captured generically by middleware
-- (app/middleware/activity_log.py) rather than call-by-call in each
-- router, so future admin endpoints are covered automatically. Powers the
-- admin "Activity Log" tab (filter by admin, filter by day).

create table admin_activity_log (
    id uuid primary key default gen_random_uuid(),
    admin_id uuid not null references admins (id),
    action text not null,
    method text not null,
    path text not null,
    detail jsonb,
    created_at timestamptz not null default now()
);

create index idx_admin_activity_log_created_at on admin_activity_log (created_at desc);
create index idx_admin_activity_log_admin_id on admin_activity_log (admin_id);

alter table admin_activity_log enable row level security;
-- No policies — same deny-by-default posture as every other table (see
-- 0004_rls_policies.sql). Only the backend's service-role key touches this.
