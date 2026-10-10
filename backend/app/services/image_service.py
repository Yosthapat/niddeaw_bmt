"""Turning an uploaded photo into the avatar the site actually serves.

Avatars are drawn at most 240 CSS px across (PlayerAvatar's "xl", on a
profile page); everywhere else they are 32-64px. A phone photo arrives at
1600px after the browser's own resize, which is three times more pixels
than the biggest slot ever needs and hundreds of KB per member — re-sent
to every visitor of the members, ranking and live pages. Shrinking to what
is drawn is the whole saving: nothing downstream can make a 1600px JPEG
cheap to send.

The same function serves the upload endpoint and the one-off script that
shrinks the avatars already in the bucket, so both produce byte-identical
output for the same input.
"""

from __future__ import annotations

import hashlib
import io

from PIL import Image, ImageOps

# 240 CSS px at a 2x device pixel ratio — the largest an avatar is ever
# drawn, on a phone with a retina screen. Bigger than this is pixels the
# browser throws away after paying to download them.
AVATAR_MAX_PX = 480

JPEG_QUALITY = 82

# JPEG has no alpha, so a transparent PNG needs something behind it. The
# app's surface colour, so a logo with a cut-out background still sits on
# the panel it is drawn on rather than on a white square.
BACKDROP = (24, 14, 19)  # --color-brand-surface, #180e13


def avatar_jpeg(data: bytes) -> bytes:
    """Re-encode an uploaded image as an avatar-sized JPEG.

    Raises ValueError if the bytes are not an image Pillow can read — the
    caller turns that into a 400 rather than storing something the site
    cannot display.
    """
    try:
        with Image.open(io.BytesIO(data)) as source:
            # Phone cameras record orientation in EXIF rather than rotating
            # the pixels, and dropping EXIF (which re-encoding does) would
            # otherwise leave portrait shots lying on their side.
            image = ImageOps.exif_transpose(source)
            if image is None:  # pragma: no cover - exif_transpose keeps the image
                image = source
            image = image.convert("RGBA") if image.mode in ("RGBA", "LA", "P") else image.convert("RGB")
            if image.mode == "RGBA":
                flattened = Image.new("RGB", image.size, BACKDROP)
                flattened.paste(image, mask=image.split()[-1])
                image = flattened

            image.thumbnail((AVATAR_MAX_PX, AVATAR_MAX_PX), Image.Resampling.LANCZOS)

            out = io.BytesIO()
            image.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except ValueError:
        raise
    except Exception as exc:  # Pillow raises a zoo of types for bad input
        raise ValueError(f"unreadable image: {exc}") from exc


def avatar_path(player_id: str, data: bytes) -> str:
    """The storage path for these exact bytes.

    Content-addressed on purpose. The avatars are served with a year-long
    cache, which is only safe if changing a photo changes its URL — reusing
    `{player_id}.jpg` would leave the old face in front of everyone who had
    already loaded it, for a year.
    """
    digest = hashlib.sha256(data).hexdigest()[:12]
    return f"{player_id}-{digest}.jpg"


def storage_path_from_url(public_url: str, bucket: str) -> str | None:
    """Recover the object path from a public URL, or None if it isn't ours.

    Used to delete the file an avatar replaces. A URL from somewhere else
    (or a shape this doesn't recognise) returns None and nothing is
    deleted, which is the safe way to be wrong here.
    """
    marker = f"/storage/v1/object/public/{bucket}/"
    _, found, tail = public_url.partition(marker)
    if not found or not tail:
        return None
    path = tail.split("?", 1)[0].strip("/")
    # One flat level of objects in this bucket; anything else is not a
    # path this module wrote.
    return path if path and "/" not in path else None
