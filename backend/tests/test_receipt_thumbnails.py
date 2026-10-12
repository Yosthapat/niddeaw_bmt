"""Thumbnails for receipts and slips.

A receipt has to stay readable — its whole purpose is the small print — so
nothing here may shrink the stored image. What it may do is put a small
copy beside it, because the lists draw a 56px square and were downloading
the full thing to fill it.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image

from app.services.image_service import (
    AVATAR_MAX_PX,
    THUMBNAIL_MAX_PX,
    avatar_jpeg,
    thumb_path,
    thumb_url,
    thumbnail_jpeg,
)
from app.services.receipt_maintenance import BUCKET, make_thumbnails
from tests.conftest import FakeSupabase

PUBLIC = "https://fake.supabase.co/storage/v1/object/public/receipts"


def photo(size: int = 1600) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (size, size), (200, 180, 160)).save(out, format="JPEG", quality=92)
    return out.getvalue()


def size_of(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.size


# --- the convention ------------------------------------------------------


def test_a_thumbnail_is_named_after_the_receipt_it_belongs_to() -> None:
    assert thumb_path("abc-123.png") == "abc-123-thumb.jpg"
    assert thumb_path("abc-123.jpeg") == "abc-123-thumb.jpg"


def test_the_same_derivation_works_on_a_public_url() -> None:
    assert thumb_url(f"{PUBLIC}/abc-123.png") == f"{PUBLIC}/abc-123-thumb.jpg"


def test_a_query_string_survives_the_derivation() -> None:
    assert thumb_url(f"{PUBLIC}/abc-123.png?t=7") == f"{PUBLIC}/abc-123-thumb.jpg?t=7"


# --- the sizes -----------------------------------------------------------


def test_a_thumbnail_is_small_enough_to_be_worth_having() -> None:
    original = photo()
    small = thumbnail_jpeg(original)
    assert max(size_of(small)) == THUMBNAIL_MAX_PX
    assert len(small) < len(original) / 20


def test_a_thumbnail_is_smaller_than_an_avatar() -> None:
    """The two sizes are drawn differently; if they ever converge, one of
    the constants was changed without thinking about the other."""
    assert THUMBNAIL_MAX_PX < AVATAR_MAX_PX
    assert len(thumbnail_jpeg(photo())) < len(avatar_jpeg(photo()))


# --- the backfill --------------------------------------------------------


def club(expenses: list[dict[str, Any]], income: list[dict[str, Any]]) -> FakeSupabase:
    fake = FakeSupabase({"expenses": expenses, "other_income": income})
    bucket = fake.storage.from_(BUCKET)
    for row in [*expenses, *income]:
        for column in ("receipt_url", "slip_url"):
            url = row.get(column)
            if url and str(url).startswith(PUBLIC):
                bucket.objects[str(url).rsplit("/", 1)[-1]] = row.pop("_bytes")
    return fake


def expense(path: str = "exp-1.jpg", data: bytes | None = None) -> dict[str, Any]:
    return {
        "id": "e1",
        "expense_date": "2026-10-10",
        "receipt_url": f"{PUBLIC}/{path}",
        "_bytes": data if data is not None else photo(),
    }


def income(path: str = "inc-1.jpg") -> dict[str, Any]:
    return {
        "id": "i1",
        "income_date": "2026-10-10",
        "slip_url": f"{PUBLIC}/{path}",
        "_bytes": photo(),
    }


def test_a_dry_run_writes_nothing() -> None:
    fake = club([expense()], [])
    report = make_thumbnails(fake, apply=False)

    assert fake.storage.from_(BUCKET).uploaded == []
    assert report.applied is False
    assert report.made == 1


def test_applying_stores_a_thumbnail_beside_the_receipt() -> None:
    fake = club([expense("exp-1.jpg")], [])
    make_thumbnails(fake, apply=True)

    (path, data, options) = fake.storage.from_(BUCKET).uploaded[0]
    assert path == "exp-1-thumb.jpg"
    assert max(size_of(data)) == THUMBNAIL_MAX_PX
    assert options["cache-control"] == "31536000"


def test_the_receipt_itself_is_never_touched() -> None:
    fake = club([expense("exp-1.jpg")], [])
    original = fake.storage.from_(BUCKET).objects["exp-1.jpg"]
    make_thumbnails(fake, apply=True)

    assert fake.storage.from_(BUCKET).objects["exp-1.jpg"] == original
    assert fake.storage.from_(BUCKET).removed == []
    # and nothing was written back over the receipt's own name
    assert all(path != "exp-1.jpg" for path, _, _ in fake.storage.from_(BUCKET).uploaded)


def test_slips_are_covered_as_well_as_receipts() -> None:
    fake = club([expense("exp-1.jpg")], [income("inc-1.jpg")])
    make_thumbnails(fake, apply=True)

    written = {path for path, _, _ in fake.storage.from_(BUCKET).uploaded}
    assert written == {"exp-1-thumb.jpg", "inc-1-thumb.jpg"}


def test_a_second_run_does_nothing() -> None:
    fake = club([expense("exp-1.jpg")], [])
    make_thumbnails(fake, apply=True)

    bucket = fake.storage.from_(BUCKET)
    (path, data, _) = bucket.uploaded[0]
    bucket.objects[path] = data
    bucket.uploaded.clear()

    report = make_thumbnails(fake, apply=True)
    assert bucket.uploaded == []
    assert (report.made, report.already, report.failed) == (0, 1, 0)


def test_a_row_with_no_receipt_is_not_in_the_report() -> None:
    fake = club([{"id": "e1", "expense_date": "2026-10-10", "receipt_url": None}], [])
    assert make_thumbnails(fake, apply=False).rows == []


def test_a_receipt_missing_from_the_bucket_is_reported_and_the_rest_still_run() -> None:
    fake = club([expense("exp-1.jpg")], [income("inc-1.jpg")])
    del fake.storage.from_(BUCKET).objects["exp-1.jpg"]

    report = make_thumbnails(fake, apply=True)
    assert (report.made, report.failed) == (1, 1)
    assert len(fake.storage.from_(BUCKET).uploaded) == 1


def test_a_stored_file_that_is_not_an_image_is_reported_not_written() -> None:
    fake = club([expense("exp-1.jpg", data=b"not an image")], [])
    report = make_thumbnails(fake, apply=True)

    assert report.failed == 1
    assert fake.storage.from_(BUCKET).uploaded == []


def test_the_totals_say_what_the_lists_stop_downloading() -> None:
    fake = club([expense("exp-1.jpg")], [income("inc-1.jpg")])
    report = make_thumbnails(fake, apply=False)

    assert report.before_total > report.after_total * 20
