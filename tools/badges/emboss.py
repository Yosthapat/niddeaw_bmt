"""Turn a real mascot PNG/WebP into an embossed-metal relief, and draw embossed number plates.

Pipeline (per mascot):
  crop by alpha -> height = blur(alpha)*0.8 + luminance*0.35 -> normals from gradient
  -> light from top-left (diffuse + specular) -> gradient-map to tier metal
  -> darkened rim + drop shadow.
"""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

import os
import urllib.request

# Chakra Petch Bold (Google Fonts, OFL). Downloaded once into .cache/ (git-ignored).
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "ChakraPetch-Bold.ttf")
FONT_URL = "https://fonts.gstatic.com/s/chakrapetch/v13/cIflMapbsEk7TDLdtEz1BwkeJI9FQA.ttf"
if not os.path.exists(FONT):
    os.makedirs(os.path.dirname(FONT), exist_ok=True)
    urllib.request.urlretrieve(FONT_URL, FONT)

# Gradient-map stops: shade 0 (deep shadow) -> 1 (specular highlight)
METALS = {
    "bronze": [(0.00, (38, 16, 6)), (0.25, (96, 46, 20)), (0.50, (160, 88, 44)),
               (0.72, (205, 132, 78)), (0.88, (238, 184, 130)), (1.00, (255, 232, 200))],
    "silver": [(0.00, (26, 30, 36)), (0.25, (78, 86, 96)), (0.50, (140, 148, 158)),
               (0.72, (190, 197, 205)), (0.88, (226, 231, 236)), (1.00, (255, 255, 255))],
    "gold":   [(0.00, (44, 26, 4)), (0.25, (120, 78, 14)), (0.50, (190, 138, 32)),
               (0.72, (230, 184, 64)), (0.88, (252, 222, 128)), (1.00, (255, 248, 214))],
}


def _ramp(name):
    stops = METALS[name]
    xs = np.array([s[0] for s in stops])
    lut = np.zeros((256, 3), np.float32)
    t = np.linspace(0, 1, 256)
    for c in range(3):
        lut[:, c] = np.interp(t, xs, [s[1][c] for s in stops])
    return lut


def _blur(arr, r):
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def _erode(arr, k):
    """Min-filter with zero padding (PIL replicates the border otherwise)."""
    pad = k
    im = Image.fromarray((np.pad(arr, pad) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(k))
    return (np.asarray(im, np.float32) / 255)[pad:-pad, pad:-pad]


def _dilate(arr, k):
    pad = k
    im = Image.fromarray((np.pad(arr, pad) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(k))
    return (np.asarray(im, np.float32) / 255)[pad:-pad, pad:-pad]


def _shade(height, alpha, metal, strength=6.0, seed=0):
    gy, gx = np.gradient(height)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(height)
    n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nx, ny, nz = nx / n, ny / n, nz / n
    L = np.array([-0.55, -0.6, 0.58]); L /= np.linalg.norm(L)       # top-left light
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    spec = np.clip(nx * H[0] + ny * H[1] + nz * H[2], 0, 1) ** 40
    # gentle vertical falloff so the top catches more light
    yy = np.linspace(0.08, -0.08, height.shape[0])[:, None]
    s = 0.12 + 0.78 * diff + 0.35 * spec + yy
    # wear: fine grain + a few soft scuffs
    rng = np.random.default_rng(seed)
    grain = rng.normal(0, 1, height.shape).astype(np.float32)
    grain = _blur((grain * 0.5 + 0.5).clip(0, 1), 0.8) - 0.5
    scuff = _blur(rng.random(height.shape).astype(np.float32), 6) - 0.5
    s = s + grain * 0.10 + scuff * 0.25
    s = np.clip(s, 0, 1)
    rgb = _ramp(metal)[(s * 255).astype(np.uint8)]
    return rgb


def emboss_mask(alpha, lum, metal, rim=True, shadow=True, seed=0, blur_r=None, strength=6.0):
    """alpha, lum: float32 HxW in 0..1. Returns RGBA Image with margin for shadow."""
    h, w = alpha.shape
    pad = int(max(h, w) * 0.08)
    A = np.pad(alpha, pad)
    Lm = np.pad(lum, pad)
    r = blur_r or max(2, max(h, w) / 90)
    height = _blur(A, r) * 0.8 + _blur(Lm * A, r * 0.35) * 0.35
    rgb = _shade(height, A, metal, strength=strength, seed=seed)

    # darker rim along the silhouette
    if rim:
        inner = _erode(A, 5)
        edge = np.clip(A - inner, 0, 1)
        edge = _blur(edge, 1.2)
        rgb = rgb * (1 - 0.55 * edge[..., None])

    out = np.zeros(A.shape + (4,), np.float32)
    out[..., :3] = rgb
    out[..., 3] = A * 255
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")

    if shadow:
        sh = Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r * 2.2))
        off = int(max(3, r * 1.4))
        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
        black = Image.new("RGBA", img.size, (0, 0, 0, 255))
        sh_a = Image.new("L", img.size, 0)
        sh_a.paste(sh.point(lambda v: int(v * 0.75)), (off, off))
        base.paste(black, (0, 0), sh_a)
        base.alpha_composite(img)
        img = base
    return img


def emboss_mascot(path, metal, target_h=440, seed=0):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.split()[-1].getbbox())
    s = target_h / im.height
    im = im.resize((round(im.width * s), target_h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    alpha = a[..., 3]
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    # clean semi-transparent fringe (ghosty feet, dark sticker outline):
    # hard-ish threshold, then open (drop specks) and close (fill hairline gaps)
    ab = _blur(alpha, 1.0)
    m = np.clip((ab - 0.6) / 0.2, 0, 1)
    m = _dilate(_erode(m, 5), 5)          # open
    m = _erode(_dilate(m, 9), 9)          # close
    alpha = _blur(m, 1.0)
    # luminance only trusted where the source was solid; elsewhere use local mean
    solid = np.clip((a[..., 3] - 0.85) / 0.15, 0, 1)
    lum = lum * solid + _blur(lum * solid, 6) / np.maximum(_blur(solid, 6), 1e-3) * (1 - solid)
    return emboss_mask(alpha, lum, metal, seed=seed)


def number_plate(text, metal, size=(300, 120), seed=1):
    """Embossed metal plate with an embossed number in Chakra Petch Bold."""
    w, h = size
    # plate shape: beveled rounded rect
    plate = Image.new("L", size, 0)
    ImageDraw.Draw(plate).rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 4, fill=255)
    P = np.asarray(plate, np.float32) / 255
    # text mask
    font = ImageFont.truetype(FONT, int(h * 0.78))
    tm = Image.new("L", size, 0)
    d = ImageDraw.Draw(tm)
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=255)
    T = np.asarray(tm, np.float32) / 255
    # height: pillowy plate + dark enamel recess band + raised digits
    inset = _erode(P, 23)
    height = _blur(P, 5) * 0.6 + _blur(T, 1.6) * 0.9 - _blur(inset, 2) * 0.15
    rgb = _shade(height, P, metal, strength=5.0, seed=seed)
    # enamel field (dark) inside the inset, digits stay metal
    enamel = np.array([16, 22, 40], np.float32)
    field = _blur(inset, 1.2) * (1 - _blur(T, 0.8))
    rgb = rgb * (1 - field[..., None] * 0.85) + enamel * field[..., None] * 0.85
    out = np.dstack([rgb, P * 255]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    # drop shadow
    pad = 16
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    sh.paste(plate, (pad + 3, pad + 5))
    sh = sh.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7))
    canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), sh)
    canvas.alpha_composite(img, (pad, pad))
    return canvas
