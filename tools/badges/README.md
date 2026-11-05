# Quest badges (เหรียญ quest)

Medal art for the quest system, in a layered 3D-metal style (back plate → frame → centre → bow → banner)
themed for นิดเดียว Badminton Club. Higher tiers carry more parts:
bronze = plain frame, silver = + shuttlecock-feather wreath, gold = + feather sunburst, pink/black bow,
queen-cat crown and a banner with the quest name.

| Shape | Category | Quests |
|---|---|---|
| circle | streak / cumulative | ไฟลุก, ขาประจำ, สายเลือดก๊วน, บ่มมานาน |
| shield | skill | ล้มยักษ์, คืนไร้พ่าย, มาราธอน, ขึ้นแท่น |
| rounded | friends | ผสมได้ทุกคู่, คู่ซี้, ล้างแค้น |
| star | monthly / limited | cat |
| diamond | secret | "?" until unlocked |

Output: `frontend/public/badges/<quest>_<level>.webp` (512px, transparent). The quest table, colours and
thresholds live in `build_all.py`.

## How a medal is made

1. **Frame** (`frames/`, AI, paid): an *empty* medal from `gen_frames.py` (OpenAI Images, transparent background).
   The centre enamel is generated black so one frame serves every quest.
2. **Mascot** (`poses/` or `frontend/public/tiers/`): always the real mascot art. New poses come from
   `gen_pose.py`, which sends the original as a reference image (Gemini kept the face best). Never let a
   model draw a mascot from scratch: the faces drift.
3. **Composite** (`build_all.py`, free): tint the enamel to the mascot's tier colour (`compose.py`), turn the
   mascot into embossed metal (`emboss.py`: alpha-cropped height map = blur(alpha)·0.8 + luminance·0.35 →
   normals → top-left light → bronze/silver/gold gradient map → dark rim + drop shadow), add the number
   plate and, on gold, engrave the quest name. Text uses Chakra Petch Bold (downloaded to `.cache/`).

```bash
pip install pillow numpy requests
python3 -I tools/badges/build_all.py               # rebuild every medal (no API calls)
python3 -I tools/badges/gen_frames.py shield:gold  # regenerate one frame (OPENAI_API_KEY, costs money)
```

Generation costs (Nov 2026, from token usage): about ฿1.8 per OpenAI `gpt-image-2.5-flare` frame and
about ฿4.5 per Gemini `gemini-3-pro-image` pose. `gpt-image-2` refuses transparent backgrounds.
