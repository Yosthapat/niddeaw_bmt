-- Drop the unused name/phone columns — nickname is now the sole identity
-- field for a player (the ชื่อจริง/เบอร์โทร admin inputs were removed).
-- Safe to run now — production currently has zero real players.

alter table players drop column name;
alter table players drop column phone;
alter table players alter column nickname set not null;
