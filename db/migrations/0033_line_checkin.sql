-- Checking yourself in by scanning a QR at the court.
--
-- Each night (session) gets its own code, made the first time an admin
-- shows the QR. The QR is a LINE link carrying that code; a linked member
-- who opens it can check themselves in to that session, and only that
-- one. A code works only while its session is open, so last week's QR —
-- photographed and passed around — checks nobody in tonight. If tonight's
-- QR leaks, the admin makes a new one and the old code stops working.
--
-- checkins.via records who did the check-in: the admin at the door, or
-- the member through LINE. Only for the admin's list; nothing is billed
-- differently.

alter table sessions
    add column line_checkin_code text
        check (line_checkin_code is null or line_checkin_code ~ '^[A-Za-z0-9_-]{12,64}$');

create unique index uq_sessions_line_checkin_code
    on sessions (line_checkin_code) where line_checkin_code is not null;

alter table checkins
    add column via text not null default 'admin' check (via in ('admin', 'line'));
