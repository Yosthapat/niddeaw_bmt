"""What the avatar pipeline must guarantee, bytes in and bytes out."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.image_service import (
    AVATAR_MAX_PX,
    avatar_jpeg,
    avatar_path,
    storage_path_from_url,
)


def photo(width: int, height: int, mode: str = "RGB", colour: object = (200, 30, 90)) -> bytes:
    """An image file of a given size, as a browser would send one."""
    image = Image.new(mode, (width, height), colour)  # type: ignore[arg-type]
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def size_of(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.size


def test_a_phone_sized_photo_comes_back_at_the_size_it_is_drawn() -> None:
    # 1600px is what the browser's own resize produces today.
    assert size_of(avatar_jpeg(photo(1600, 1600))) == (AVATAR_MAX_PX, AVATAR_MAX_PX)


def test_the_long_edge_is_what_gets_capped() -> None:
    assert size_of(avatar_jpeg(photo(1600, 900))) == (AVATAR_MAX_PX, 270)
    assert size_of(avatar_jpeg(photo(900, 1600))) == (270, AVATAR_MAX_PX)


def test_a_photo_already_small_enough_is_not_blown_up() -> None:
    assert size_of(avatar_jpeg(photo(120, 120))) == (120, 120)


def test_the_result_is_a_jpeg_whatever_arrived() -> None:
    with Image.open(io.BytesIO(avatar_jpeg(photo(800, 800)))) as image:
        assert image.format == "JPEG"


def test_a_transparent_png_lands_on_the_app_background_not_a_white_square() -> None:
    transparent = photo(600, 600, mode="RGBA", colour=(0, 0, 0, 0))
    with Image.open(io.BytesIO(avatar_jpeg(transparent))) as image:
        assert image.mode == "RGB"
        # The surface colour, give or take JPEG's own rounding.
        r, g, b = image.getpixel((10, 10))  # type: ignore[misc]
        assert abs(r - 24) < 12 and abs(g - 14) < 12 and abs(b - 19) < 12


def test_shrinking_actually_shrinks() -> None:
    original = photo(1600, 1600)
    assert len(avatar_jpeg(original)) < len(original) / 4


def test_something_that_is_not_an_image_is_rejected_rather_than_stored() -> None:
    with pytest.raises(ValueError):
        avatar_jpeg(b"this is not a photo, it is a sentence")


def test_the_stored_name_changes_when_the_photo_does() -> None:
    player = "11111111-1111-1111-1111-111111111111"
    one = avatar_jpeg(photo(400, 400, colour=(10, 20, 30)))
    two = avatar_jpeg(photo(400, 400, colour=(200, 100, 50)))
    assert avatar_path(player, one) != avatar_path(player, two)


def test_the_stored_name_is_stable_for_the_same_photo() -> None:
    player = "11111111-1111-1111-1111-111111111111"
    data = avatar_jpeg(photo(400, 400))
    assert avatar_path(player, data) == avatar_path(player, data)


def test_the_stored_name_carries_the_player_so_a_bucket_listing_reads() -> None:
    player = "11111111-1111-1111-1111-111111111111"
    name = avatar_path(player, avatar_jpeg(photo(400, 400)))
    assert name.startswith(player) and name.endswith(".jpg")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://x.supabase.co/storage/v1/object/public/avatars/abc-123.jpg",
            "abc-123.jpg",
        ),
        (
            "https://x.supabase.co/storage/v1/object/public/avatars/abc-123.jpg?t=1",
            "abc-123.jpg",
        ),
        # Another bucket, a nested path, or a URL from anywhere else: not
        # ours to delete.
        ("https://x.supabase.co/storage/v1/object/public/receipts/abc.jpg", None),
        ("https://x.supabase.co/storage/v1/object/public/avatars/nested/abc.jpg", None),
        ("https://cdn.example.com/someone-elses/abc.jpg", None),
        ("", None),
    ],
)
def test_only_this_buckets_own_flat_objects_are_recognised(url: str, expected: str | None) -> None:
    assert storage_path_from_url(url, "avatars") == expected
