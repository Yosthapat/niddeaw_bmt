"""Turning whatever a sponsor sends into a logo that sits in the band.

Every logo on the home page's sponsor band is the same white silhouette,
trimmed to the mark itself, so six brands with six colour schemes read as
one row instead of a patchwork of boxes. The first five were made by hand;
this does the same to an upload, so an admin can add a sponsor from a
phone with whatever file the sponsor sent — a transparent PNG, or a JPG
with a white (or any flat) background.

Two ways to make it white (`mode`):
- "shape": everything that is the logo turns white. Right for most files.
- "light": only the light parts turn white and the dark ones drop out, for
  logos drawn light-on-dark: a dark badge behind the lettering, or a dark
  textured background (stone, wood) that "shape" would keep as speckle.

Pure Pillow, no state: the admin preview and the save call the same
function, so what was previewed is what gets stored.
"""

from __future__ import annotations

import hashlib
import io
from collections import deque
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageChops, ImageFilter, ImageOps

LogoMode = Literal["shape", "light"]

# The band draws a logo at most ~240 CSS px wide; twice that for a retina
# phone. The hand-made five are 323-449px across.
LOGO_MAX_PX = 480

# How far a pixel must be from the background colour before it counts as
# logo. Below LOW it is background; above HIGH it is fully logo; between,
# it fades — which keeps anti-aliased edges smooth instead of jagged.
LOW = 28
HIGH = 80

# A border this transparent means the file already has a cut-out
# background and its alpha is the mask.
TRANSPARENT_BORDER_SHARE = 0.5

# "light" mode works on a copy no bigger than this (the result is at most
# LOGO_MAX_PX anyway), which keeps its speck search quick on a phone photo.
LIGHT_WORK_PX = 900
# A bright patch smaller than this share of the picture is texture, not
# lettering (about 120px of a 958px square).
LIGHT_MIN_AREA_SHARE = 0.00013


@dataclass(frozen=True)
class Logo:
    png: bytes
    width: int
    height: int


def _border_pixels(image: Image.Image) -> list[tuple[int, ...]]:
    w, h = image.size
    step = max(1, min(w, h) // 64)
    pixels = image.load()
    assert pixels is not None
    points = (
        [(x, 0) for x in range(0, w, step)]
        + [(x, h - 1) for x in range(0, w, step)]
        + [(0, y) for y in range(0, h, step)]
        + [(w - 1, y) for y in range(0, h, step)]
    )
    return [tuple(pixels[p]) for p in points]  # type: ignore[arg-type]


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _mask(image: Image.Image) -> Image.Image:
    """An L image: 255 where the logo is, 0 where the background is."""
    border = _border_pixels(image)
    alpha = image.getchannel("A")
    if sum(1 for p in border if p[3] < 16) >= TRANSPARENT_BORDER_SHARE * len(border):
        return alpha

    # A flat background: its colour is whatever the edge of the picture
    # mostly is. Distance from it, per channel, worst channel wins — so a
    # dark logo on white and a white logo on red both separate cleanly.
    background = tuple(_median([p[i] for p in border]) for i in range(3))
    rgb = image.convert("RGB")
    flat = Image.new("RGB", rgb.size, background)
    diff = ImageChops.difference(rgb, flat)
    r, g, b = diff.split()
    distance = ImageChops.lighter(ImageChops.lighter(r, g), b)
    span = HIGH - LOW
    ramp = distance.point(lambda v: 0 if v <= LOW else 255 if v >= HIGH else (v - LOW) * 255 // span)
    return ImageChops.multiply(ramp, alpha)


def _light_mask(image: Image.Image) -> Image.Image:
    """An L image of the parts brighter than the background.

    The cut-off sits just above the brightest of the background, sampled
    along the edges (transparent counts as dark). Bright specks of a
    textured background are dropped by keeping only connected bright areas
    big enough to be lettering; shaded strokes are closed up, and a soft
    edge allowed just outside them.
    """
    alpha = image.getchannel("A")
    lum = ImageChops.multiply(image.convert("L"), alpha)
    w, h = lum.size
    step = max(1, min(w, h) // 200)
    px = lum.load()
    assert px is not None
    edge = sorted(
        [int(px[x, y]) for x in range(0, w, step) for y in (0, h - 1)]  # type: ignore[arg-type]
        + [int(px[x, y]) for y in range(0, h, step) for x in (0, w - 1)]  # type: ignore[arg-type]
    )
    cut = max(60, min(200, edge[int(len(edge) * 0.99)] + 15))

    bright = lum.tobytes()
    n = w * h
    min_area = max(12, round(n * LIGHT_MIN_AREA_SHARE))
    seen = bytearray(n)
    keep = bytearray(n)
    for start in range(n):
        if seen[start] or bright[start] < cut:
            continue
        seen[start] = 1
        queue = deque([start])
        comp = []
        while queue:
            p = queue.popleft()
            comp.append(p)
            x = p % w
            for q in (p - 1 if x else -1, p + 1 if x < w - 1 else -1, p - w, p + w):
                if 0 <= q < n and not seen[q] and bright[q] >= cut:
                    seen[q] = 1
                    queue.append(q)
        if len(comp) >= min_area:
            for p in comp:
                keep[p] = 255

    kept = Image.frombytes("L", (w, h), bytes(keep))
    solid = kept.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    near = solid.filter(ImageFilter.MaxFilter(5))
    lo, hi = cut - 45, cut + 15

    def ramp(v: int) -> int:
        t = min(1.0, max(0.0, (v - lo) / (hi - lo)))
        return round(255 * t * t * (3 - 2 * t))

    soft = ImageChops.multiply(lum.point(ramp), near)
    return ImageChops.lighter(ImageChops.multiply(solid, alpha), soft)


def white_silhouette(data: bytes, mode: LogoMode = "shape") -> Logo:
    """The logo in `data` as a trimmed white-on-transparent PNG.

    Raises ValueError when the bytes are not an image, or when nothing in
    the picture stands out from its background (a blank or one-colour
    file) — the caller says so rather than storing an invisible logo.
    """
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source) or source
            image = image.convert("RGBA")
    except Exception as exc:  # Pillow raises a zoo of types for bad input
        raise ValueError(f"unreadable image: {exc}") from exc

    if mode == "light":
        image.thumbnail((LIGHT_WORK_PX, LIGHT_WORK_PX), Image.Resampling.LANCZOS)
        mask = _light_mask(image)
    else:
        mask = _mask(image)
    # Trim to the mark, ignoring faint specks (JPEG noise on a "white"
    # background is never quite 255).
    box = mask.point(lambda v: 255 if v > 24 else 0).getbbox()
    if box is None:
        raise ValueError("no logo found")
    mask = mask.crop(box)
    mask.thumbnail((LOGO_MAX_PX, LOGO_MAX_PX), Image.Resampling.LANCZOS)

    white = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    white.putalpha(mask)
    out = io.BytesIO()
    white.save(out, format="PNG", optimize=True)
    return Logo(png=out.getvalue(), width=mask.width, height=mask.height)


def logo_path(png: bytes) -> str:
    """Content-addressed, like avatars: the files are cached for a year,
    so a new logo has to be a new URL."""
    return f"{hashlib.sha256(png).hexdigest()[:16]}.png"
