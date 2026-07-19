-- Seed the singleton club_settings row. promptpay_id is left blank
-- deliberately — never commit a real PromptPay ID to git. Admin fills this
-- in via Admin > Settings on first login.
insert into club_settings (id, promptpay_id, promptpay_type, default_rate_per_hour)
values (1, '', 'phone', 0)
on conflict (id) do nothing;
