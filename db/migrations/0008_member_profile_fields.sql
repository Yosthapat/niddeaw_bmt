-- Member profile fields: auto-numbered member code, dominant hand, and
-- social handles.
--
-- member_seq is a serial so every player (existing and future) gets a
-- permanent, monotonically increasing number; the display code (e.g.
-- "ND007") is computed from it in the API layer (Player.member_code),
-- not stored redundantly.

alter table players add column member_seq serial unique;
alter table players add column dominant_hand text check (dominant_hand in ('left', 'right'));
alter table players add column tiktok text;
alter table players add column instagram text;
