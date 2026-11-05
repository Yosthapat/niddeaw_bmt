"""Medal composer helpers: tint the frame's black enamel to the quest colour, find the gold banner,
engrave Thai text on it (Chakra Petch via Pillow's raqm layout)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from emboss import emboss_mascot, number_plate, FONT, _blur, _dilate, _erode

# enamel colours = the app's --color-tier-* / TIER_CARD dark tones
ENAMEL = {"milk": "#5c574c", "beer": "#6e4a05", "highball": "#7a2c0c", "wine": "#3d1220", "soju": "#2f6b3c",
          "whisky": "#4d1d14", "vodka": "#3d1680", "absinthe": "#4b3f9e", "navy": "#1b2a5c", "pink": "#79004e"}


def hex_rgb(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def enamel_mask(frame):
    a = np.asarray(frame, np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    sat = a[..., :3].max(-1) - a[..., :3].min(-1)
    cand = (a[..., 3] > 200) & (lum < 120) & (sat < 40)
    h, w = cand.shape
    seen = np.zeros_like(cand)
    q = deque([(h // 2, w // 2)]); seen[h // 2, w // 2] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    m = _erode(_dilate(seen.astype(np.float32), 7), 7)    # fill specular holes
    return seen, m, lum


def tint_enamel(frame, color):
    a = np.asarray(frame, np.float32).copy()
    _, m, lum = enamel_mask(frame)
    m = _blur(m, 1.0)
    c = hex_rgb(color)
    lum_c = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    if lum_c > 34:                      # keep hue, cap brightness so metal reliefs pop
        c = c * (34 / lum_c)
    L = lum / 255.0
    base = c * (0.45 + np.clip(L * 5, 0, 1) * 0.55)[..., None]           # body colour, shaded by original
    hi = (np.clip(L - 0.18, 0, 1) * 1.6)[..., None] * 255                   # keep glossy highlight
    new = np.clip(base + hi, 0, 255)
    a[..., :3] = a[..., :3] * (1 - m[..., None]) + new * m[..., None]
    ys, xs = np.nonzero(m > 0.5)
    return Image.fromarray(a.astype(np.uint8), "RGBA"), (xs.min(), ys.min(), xs.max(), ys.max())


def find_banner(frame, cx, enamel_bottom):
    """Blank gold banner below the enamel: longest run of bright pixels on the centre column."""
    a = np.asarray(frame.convert("RGBA"), np.float32)
    col = a[:, cx - 20:cx + 20]
    lum = (0.299 * col[..., 0] + 0.587 * col[..., 1] + 0.114 * col[..., 2]).mean(1)
    al = col[..., 3].mean(1)
    best, run, start = None, 0, 0
    for y in range(enamel_bottom + 15, a.shape[0]):
        if lum[y] > 120 and al[y] > 200:
            if run == 0:
                start = y
            run += 1
            if best is None or run > best[1]:
                best = (start, run)
        else:
            run = 0
    if best and best[1] > 40:
        return best[0] + best[1] // 2, best[1]
    return None


def engrave(img, text, center, height, max_w):
    """Debossed text: dark fill, light lip at bottom-right, shadow at top-left."""
    size = int(height)
    font = ImageFont.truetype(FONT, size)
    while font.getlength(text) > max_w and size > 10:
        size -= 2; font = ImageFont.truetype(FONT, size)
    W, H = img.size
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).text(center, text, font=font, fill=255, anchor="mm")
    M = np.asarray(m, np.float32) / 255
    sh = np.roll(np.roll(M, -2, 0), -2, 1)   # rim lit
    lip = np.roll(np.roll(M, 2, 0), 2, 1)
    a = np.asarray(img, np.float32).copy()
    rgb = a[..., :3]
    rgb = rgb * (1 - np.clip(lip - M, 0, 1)[..., None] * 0.5) + 255 * np.clip(lip - M, 0, 1)[..., None] * 0.5
    rgb = rgb * (1 - np.clip(sh - M, 0, 1)[..., None] * 0.6)
    rgb = rgb * (1 - M[..., None] * 0.72) + np.array([40, 20, 4]) * M[..., None] * 0.3
    a[..., :3] = rgb
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")

