"""Turning whatever a sponsor sends into a logo that sits in the band.

Every logo on the home page's sponsor band is the same white silhouette,
trimmed to the mark itself, so six brands with six colour schemes read as
one row instead of a patchwork of boxes. The first five were made by hand;
this does the same to an upload, so an admin can add a sponsor from a
phone with whatever file the sponsor sent — a transparent PNG, or a JPG
with a white (or any flat) background.

Pure Pillow, no state: the admin preview and the save call the same
function, so what was previewed is what gets stored.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageOps

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


def white_silhouette(data: bytes) -> Logo:
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
