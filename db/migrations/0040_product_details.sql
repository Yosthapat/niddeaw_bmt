-- Close-ups for a product's cinematic page: up to three pictures of its
-- details (the chest logo, the print on the back, the sponsors), each with
-- a short label and a line under it. Shown under the turnaround clip
-- (0039). A product without them simply skips that part of the page.
--
--   detail_images  [{"url": "...", "label": "FRONT", "note": "..."}, ...]
--
-- Run once, after 0039_product_video.sql.

alter table products add column if not exists detail_images jsonb not null default '[]'::jsonb;
