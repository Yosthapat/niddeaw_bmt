-- The words on a product's cinematic page (0039, 0040): the short name on
-- the stage, the line under it, the captions that come up while the clip
-- turns, the fabric's selling points, which photos make the lookbook, and
-- the size chart (inches). All optional; the page falls back to the
-- product's own name and photos.
--
--   cinema  {"title": "JERSEY #01", "subtitle": "...",
--            "captions": [{"label": "THE CAT", "text": "..."}, ...],
--            "facts": ["ระบายอากาศดี", ...],
--            "lookbook": ["<photo url>", ...],
--            "chart": [{"size": "XS", "width": 36, "length": 25}, ...]}
--
-- Run once, after 0040_product_details.sql. The update at the end fills it
-- in for Jersey #01; the admin can change every part on the product form.

alter table products add column if not exists cinema jsonb not null default '{}'::jsonb;

update products set cinema = '{
  "title": "JERSEY #01",
  "subtitle": "เสื้อทีมก๊วนนิดเดียว · พรีออเดอร์",
  "captions": [
    {"label": "PINK × BLACK", "text": "ชมพูตัดดำ ใส่ได้ทั้งชายและหญิง"},
    {"label": "THE CAT", "text": "แมวดำวิ่งเต็มแผ่นหลัง"},
    {"label": "LIGHT · DRY", "text": "ผ้าเบา ระบายอากาศ แห้งไว"}
  ],
  "facts": ["เนื้อผ้าน้ำหนักเบา", "ระบายอากาศดี", "แห้งไว ไม่อับชื้น", "ยืดหยุ่น", "Unisex"],
  "chart": [
    {"size": "XS", "width": 36, "length": 25}, {"size": "S", "width": 38, "length": 26},
    {"size": "M", "width": 40, "length": 27}, {"size": "L", "width": 42, "length": 28},
    {"size": "XL", "width": 44, "length": 29}, {"size": "2XL", "width": 46, "length": 30},
    {"size": "3XL", "width": 48, "length": 31}, {"size": "4XL", "width": 50, "length": 32},
    {"size": "5XL", "width": 52, "length": 33}
  ]
}'::jsonb
  -- the lookbook: its two photos of the shirt being worn (front, back)
  || case when cardinality(image_urls) >= 3
       then jsonb_build_object('lookbook', jsonb_build_array(image_urls[2], image_urls[3]))
       else '{}'::jsonb end
where name = 'Niddeaw jersey shirt #01' and cinema = '{}'::jsonb;
