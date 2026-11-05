"""Chroma-key removal for image models that cannot output transparency (Gemini)."""
from collections import deque
import numpy as np
from PIL import Image, ImageFilter


def key_out(im, key="green", despill_all=True):
    a = np.asarray(im, np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    if key == "magenta":
        greenness = np.minimum(r, b) - g          # >0 means magenta-dominant
    else:
        greenness = g - np.maximum(r, b)              # >0 means green-dominant
    bgmask = greenness > 60
    # only background connected to the border (don't punch holes in green-ish reflections)
    h, w = bgmask.shape
    seen = np.zeros_like(bgmask)
    q = deque([(y, x) for y in (0, h - 1) for x in range(w) if bgmask[y, x]] +
              [(y, x) for x in (0, w - 1) for y in range(h) if bgmask[y, x]])
    for y, x in q: seen[y, x] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and bgmask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    alpha = (~seen).astype(np.float32)
    # soft edge from greenness in a thin band
    band = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    soft = np.clip(1 - (greenness - 15) / 60, 0, 1)
    alpha = np.where((band > 0.02) & (band < 0.98), np.minimum(band, soft), alpha)
    # despill: clamp green to max(r,b) near the edge / everywhere it dominates
    if key == "magenta":
        # remove the shared magenta component (min(r,b) above g) only in the soft edge band
        edge = alpha < 0.999
        spill = np.where(edge, np.clip(np.minimum(r, b) - g, 0, None), 0)
        out = np.dstack([r - spill, g, b - spill, alpha * 255]).clip(0, 255).astype(np.uint8)
    else:
        spill_zone = (greenness > 0) if despill_all else ((greenness > 0) & (alpha < 0.999))
        g2 = np.where(spill_zone, np.maximum(r, b), g)
        out = np.dstack([r, g2, b, alpha * 255]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")
