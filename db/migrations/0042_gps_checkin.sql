-- Checking yourself in by where you are, instead of scanning the QR.
--
-- At the court an admin pins tonight's spot from their phone (its GPS),
-- with a radius. A linked member who opens "เช็กอิน" in LINE and whose
-- phone is inside that circle is checked in to tonight in one tap. A
-- night with no pin checks nobody in this way; a closed night never does.
--
-- checkins.via gains 'gps', so the admin's list shows who came in this way.

alter table sessions
    add column checkin_lat double precision check (checkin_lat between -90 and 90),
    add column checkin_lng double precision check (checkin_lng between -180 and 180),
    add column checkin_radius_m integer check (checkin_radius_m between 30 and 500),
    add column checkin_accuracy_m integer check (checkin_accuracy_m >= 0),
    add column checkin_pinned_at timestamptz;

-- a pin is all of it or none of it
alter table sessions
    add constraint sessions_checkin_spot_whole check (
        (checkin_lat is null) = (checkin_lng is null)
        and (checkin_lat is null) = (checkin_radius_m is null)
    );

alter table checkins drop constraint if exists checkins_via_check;
alter table checkins
    add constraint checkins_via_check check (via in ('admin', 'line', 'gps'));
