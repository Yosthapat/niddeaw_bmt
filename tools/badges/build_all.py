"""Build every quest medal from the 15 frames + mascots.

  python3 -I tools/badges/build_all.py            # all medals
  python3 -I tools/badges/build_all.py fire aged  # only quests whose id starts with these

Writes frontend/public/badges/<quest>_<level>.webp (512px, for the web app),
plus 1024px PNG masters and a dark contact sheet in tools/badges/out/ (git-ignored).
No image-model calls here: re-running is free.
"""
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from emboss import emboss_mascot, emboss_mask, number_plate, FONT
from compose import tint_enamel, engrave, find_banner, ENAMEL

ROOT = os.path.abspath(os.path.join(S, "..", ".."))
T = os.path.join(ROOT, "frontend/public/tiers/")
CAT = os.path.join(ROOT, "frontend/public/hero/cat-color.webp")
P = os.path.join(S, "poses/")
OUT = os.path.join(S, "out/medals")                       # 1024px PNG masters (git-ignored)
WEB = os.path.join(ROOT, "frontend/public/badges")        # 512px WebP for the app
WEB_SIZE = 512
METAL = {"bronze": "bronze", "silver": "silver", "gold": "gold"}

# per-shape layout: mascot box (fraction of enamel h / w), vertical offset, plate centre (fraction of enamel h from top)
LAYOUT = {
    "circle":  dict(h=0.66, w=0.62, dy=-0.07, plate=0.92),
    "shield":  dict(h=0.62, w=0.62, dy=-0.08, plate=0.88),
    "rounded": dict(h=0.66, w=0.70, dy=-0.07, plate=0.92),
    "star":    dict(h=0.66, w=0.62, dy=-0.07, plate=0.92),
    "diamond": dict(h=0.48, w=0.42, dy=-0.06, plate=0.78),
}

# (id, title, shape, enamel, mascots, [(tier, label), ...])
QUESTS = [
    ("fire", "ไฟลุก", "circle", "vodka", [P + "vodka_fist.webp"], [("bronze", 3), ("silver", 5), ("gold", 10)]),
    ("regular", "ขาประจำ", "circle", "beer", [P + "beer_regular.webp"], [("bronze", 5), ("silver", 20), ("gold", 50)]),
    ("bloodline", "สายเลือดก๊วน", "circle", "wine", [P + "wine_loyal.webp"], [("bronze", 4), ("silver", 8), ("gold", 12)]),
    ("aged", "บ่มมานาน", "circle", "whisky", [P + "whisky_aged.webp"],
        [("bronze", 10), ("silver", 50), ("gold", 100), ("gold", 300, "pink")]),   # 300 = gold on brand-pink enamel
    ("giant", "ล้มยักษ์", "shield", "milk", [P + "milk_giant.webp"], [("bronze", 1), ("silver", 5), ("gold", 10)]),
    ("unbeaten", "คืนไร้พ่าย", "shield", "absinthe", [P + "absinthe_unbeaten.webp"], [("bronze", 1), ("silver", 3), ("gold", 5)]),
    ("marathon", "มาราธอน", "shield", "soju", [P + "soju_marathon.webp"], [("bronze", 6), ("silver", 7), ("gold", 8)]),
    ("mixer", "ผสมได้ทุกคู่", "rounded", "highball", [P + "highball_mixer.webp"], [("bronze", 5), ("silver", 10), ("gold", 20)]),
    ("buddy", "คู่ซี้", "rounded", "soju", [P + "soju_buddy.webp", P + "highball_buddy.webp"], [("bronze", 5), ("silver", 10), ("gold", 20)]),
    ("revenge", "ล้างแค้น", "rounded", "whisky", [P + "whisky_revenge.webp"], [("silver", 1), ("gold", 3)]),
    ("monthly", "นิดเดียว", "star", "pink", [CAT], [("bronze", None), ("silver", None), ("gold", None)]),
    ("secret", "ลับ", "diamond", "#1c1622", ["?"], [("bronze", None), ("silver", None), ("gold", None)]),
]
# ขึ้นแท่น: one medal per ELO tier, original mascot, plate = tier's starting ELO
PODIUM = [("milk", 800, "bronze"), ("beer", 1000, "bronze"), ("highball", 1200, "bronze"),
          ("wine", 1400, "silver"), ("soju", 1600, "silver"), ("whisky", 1800, "silver"),
          ("vodka", 2000, "gold"), ("absinthe", 2200, "gold")]
for tier, score, metal in PODIUM:
    QUESTS.append((f"podium_{tier}", "ขึ้นแท่น", "shield", tier, [T + tier + ".webp"], [(metal, score)]))


def relief_fit(src, metal, max_h, max_w, seed):
    if src == "?":
        size = int(max_h)
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).text((size // 2, size // 2), "?", font=ImageFont.truetype(FONT, int(size * 1.1)), fill=255, anchor="mm")
        m = m.crop(m.getbbox())
        a = np.asarray(m, np.float32) / 255
        return emboss_mask(a, a * 0.5, metal, seed=seed)
    r = emboss_mascot(src, metal, target_h=int(max_h), seed=seed)
    bb = r.split()[-1].getbbox()
    vis_w = bb[2] - bb[0]
    if vis_w > max_w:
        r = emboss_mascot(src, metal, target_h=int(max_h * max_w / vis_w), seed=seed)
    return r


def build(qid, title, shape, enamel, mascots, tier, label, enamel_override=None):
    frame = Image.open(os.path.join(S, f"frames/{shape}_{tier}.webp")).convert("RGBA")
    col = ENAMEL.get(enamel_override or enamel, enamel_override or enamel)
    frame, (x0, y0, x1, y1) = tint_enamel(frame, col)
    ew, eh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    L = LAYOUT[shape]
    out = frame.copy()
    n = len(mascots)
    for i, src in enumerate(mascots):
        sh = 0.82 if n > 1 else 1.0
        r = relief_fit(src, METAL[tier], eh * L["h"] * sh, ew * L["w"] / n * 1.1, seed=i + len(qid))
        bb = r.split()[-1].getbbox()
        mx = cx if n == 1 else int(cx + (i - (n - 1) / 2) * ew * 0.36)
        my = cy + int(eh * L["dy"])
        out.alpha_composite(r, (mx - (bb[0] + bb[2]) // 2, my - (bb[1] + bb[3]) // 2))
    if label is not None:
        txt = str(label)
        pw = int(ew * (0.40 if len(txt) <= 2 else 0.50))
        plate = number_plate(txt, METAL[tier], size=(pw, int(ew * 0.16)))
        py = y0 + int(eh * L["plate"])
        out.alpha_composite(plate, (cx - plate.width // 2, py - plate.height // 2))
    if tier == "gold":
        b = find_banner(frame, cx, y1)
        if b:
            out = engrave(out, title, (cx, b[0]), b[1] * 0.60, ew * 0.95)
    name = f"{qid}_{label if label is not None else tier}"
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WEB, exist_ok=True)
    out.save(os.path.join(OUT, name + ".png"))
    out.resize((WEB_SIZE, WEB_SIZE), Image.LANCZOS).save(os.path.join(WEB, name + ".webp"), quality=88, alpha_quality=100, method=6)
    return name + ".png"


def sheet(items, path, cols, cell=300, bg=(12, 8, 10)):
    rows = (len(items) + cols - 1) // cols
    f = ImageFont.truetype(FONT, 22)
    im = Image.new("RGBA", (cols * cell, rows * (cell + 34)), bg + (255,))
    d = ImageDraw.Draw(im)
    for k, (fn, cap) in enumerate(items):
        x, y = (k % cols) * cell, (k // cols) * (cell + 34)
        im.alpha_composite(Image.open(os.path.join(OUT, fn)).resize((cell, cell), Image.LANCZOS), (x, y))
        d.text((x + cell // 2, y + cell + 14), cap, font=f, fill=(246, 169, 205), anchor="mm")
    im.convert("RGB").save(path)


if __name__ == "__main__":
    only = sys.argv[1:]
    built = []
    for q in QUESTS:
        qid, title, shape, enamel, mascots, levels = q
        if only and not any(qid.startswith(o) for o in only):
            continue
        for lv in levels:
            tier, label = lv[0], lv[1]
            ov = lv[2] if len(lv) > 2 else None
            fn = build(qid, title, shape, enamel, mascots, tier, label, ov)
            cap = f"{title} {label}" if label is not None and not qid.startswith("podium") else \
                  (f"{qid.split('_')[1].capitalize()} {label}" if qid.startswith("podium") else f"{title} · {tier}")
            built.append((fn, cap))
            print(fn)
    print(len(built), "medals")
    sheet(built, os.path.join(S, "out/all_medals_dark.png"), cols=8)
