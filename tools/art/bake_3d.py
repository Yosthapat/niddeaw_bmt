"""Turn the flat cat logo into the 3D one the home page shows.

    python tools/art/bake_3d.py            # writes frontend/public/hero/cat-3d.webp

The logo is a flat cartoon: black outlines around flat colour. This puffs
every region the outline encloses (crown, ears, head, body, tail, paw) up
on its own, like a vinyl toy, then lights it: from the upper left with a
glossy highlight, darker where a surface tucks into its outline, and a neon
pink rim on the right where the hero's light would catch it.

No 3D model and no AI render: a height field per region, normals from its
slope, and three lights. Needs Pillow and numpy only. Re-run it if the logo
in tools/art/cat-source.png changes; it must keep a transparent background.
"""
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / 'cat-source.png'
OUT = HERE.parent.parent / 'frontend' / 'public' / 'hero' / 'cat-3d.webp'

BEVEL = 64          # px (at source size) over which a surface rises from its edge
OUT_WIDTH = 1000    # 2x the widest it is drawn on the page


def shift(m: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = m[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
    return out


def distance(mask: np.ndarray, cap: int) -> np.ndarray:
    """Pixels to the region's edge, up to `cap`, by repeated erosion.
    Alternating 4- and 8-neighbour steps approximates a round falloff."""
    n4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    n8 = n4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    d = np.zeros(mask.shape, np.float32)
    cur = mask.copy()
    for i in range(cap):
        d += cur
        nxt = cur.copy()
        for dy, dx in n8 if i % 2 else n4:
            nxt &= shift(cur, dy, dx)
        cur = nxt
        if not cur.any():
            break
    return d


def blur(x: np.ndarray, r: int) -> np.ndarray:
    """Three box blurs in each direction, which is close to a gaussian."""
    k = 2 * r + 1
    for _ in range(3):
        c = np.cumsum(np.pad(x, ((r + 1, r), (0, 0)), mode='edge'), axis=0)
        x = (c[k:] - c[:-k]) / k
        c = np.cumsum(np.pad(x, ((0, 0), (r + 1, r)), mode='edge'), axis=1)
        x = (c[:, k:] - c[:, :-k]) / k
    return x


def unit(v: list[float]) -> np.ndarray:
    a = np.array(v, np.float32)
    return a / np.linalg.norm(a)


def main() -> None:
    px = np.asarray(Image.open(SRC).convert('RGBA')).astype(np.float32) / 255
    rgb, alpha = px[..., :3], px[..., 3]
    solid = alpha > 0.5
    ink = solid & (rgb.max(axis=2) < 0.30)          # the black outline and the eye
    fill = solid & ~ink

    # Height: a round bevel on every colour region, the outline as a low piping.
    d = distance(fill, BEVEL)
    t = np.minimum(d, BEVEL) / BEVEL
    height = BEVEL * np.sqrt(1 - (1 - t) ** 2)
    height += 3.0 * np.minimum(distance(ink, 6), 6) / 6
    height = blur(height, 4)

    gy, gx = np.gradient(height)
    normal = np.dstack([-gx * 0.9, -gy * 0.9, np.ones_like(height)])
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)

    key = unit([-0.45, -0.62, 0.64])                 # upper left, in front
    half = unit(list(key + np.array([0, 0, 1.0])))
    diffuse = np.clip(normal @ key, 0, 1)
    specular = np.clip(normal @ half, 0, 1) ** 60
    occlusion = np.where(ink, 1.0, 0.84 + 0.16 * np.clip(d / 14, 0, 1))

    colour = rgb * ((0.70 + 0.40 * diffuse) * occlusion)[..., None]
    colour += (specular * np.where(ink, 0.35, 0.6))[..., None]

    # The pink rim: only on the outer contour, only where it faces right.
    edge = np.clip(1 - distance(solid, 18) / 18, 0, 1) ** 1.5
    rim = edge * np.clip(normal @ unit([0.85, 0.15, 0.5]), 0, 1)
    colour += rim[..., None] * np.array([0.93, 0.30, 0.64]) * 0.85

    img = Image.fromarray((np.dstack([np.clip(colour, 0, 1), alpha]) * 255).round().astype(np.uint8), 'RGBA')
    img = img.crop(img.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    img = img.resize((OUT_WIDTH, round(img.height * OUT_WIDTH / img.width)), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, 'WEBP', quality=90, method=6)
    print(f'wrote {OUT.relative_to(HERE.parent.parent)} {img.width}x{img.height}')


if __name__ == '__main__':
    main()
