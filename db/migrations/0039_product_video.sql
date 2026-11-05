-- A product can carry a short clip of itself turning round (a model in the
-- shirt, say). The product page then opens on it, playing in a loop under a
-- spotlight. Optional: a product without one keeps the photo page.
--
-- The file lives in the public 'shop' bucket next to the photos.
--
-- Run once, after 0038_quests.sql.

alter table products add column if not exists video_url text;
