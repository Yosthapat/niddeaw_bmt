-- Creates the public "avatars" Storage bucket used by
-- POST /api/admin/players/{id}/avatar. Public read (so avatar URLs work
-- directly in <img> tags on the public Member List) — writes only ever
-- happen through the backend's service-role key.
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true)
on conflict (id) do nothing;
