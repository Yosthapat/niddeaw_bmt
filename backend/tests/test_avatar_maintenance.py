"""The pass that rewrites the avatars already in the bucket.

Run against the club's real data from the admin screen or a terminal, so
what matters here is that a dry run writes nothing, a second run is a
no-op, one bad photo does not stop the rest, and the old file is only
deleted once the member points at the new one.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image

from app.services.avatar_maintenance import AVATAR_BUCKET, shrink_all
from tests.conftest import FakeSupabase

PUBLIC = "https://fake.supabase.co/storage/v1/object/public/avatars"
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"


def photo(size: int = 1600, colour: tuple[int, int, int] = (200, 30, 90)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (size, size), colour).save(out, format="JPEG", quality=95)
    return out.getvalue()


def club(*players: dict[str, Any]) -> FakeSupabase:
    """A fake holding these members, with each one's photo in the bucket."""
    fake = FakeSupabase({"players": list(players)})
    bucket = fake.storage.from_(AVATAR_BUCKET)
    for player in players:
        url = player.get("avatar_url")
        if url and url.startswith(PUBLIC):
            bucket.objects[url.rsplit("/", 1)[-1]] = player.pop("_bytes")
    return fake


def member(
    player_id: str, nickname: str, *, path: str | None, data: bytes | None = None
) -> dict[str, Any]:
    if path is None:
        return {"id": player_id, "nickname": nickname, "avatar_url": None}
    return {
        "id": player_id,
        "nickname": nickname,
        "avatar_url": f"{PUBLIC}/{path}",
        "_bytes": data if data is not None else photo(),
    }


def test_a_dry_run_writes_nothing() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"))
    report = shrink_all(fake, apply=False)

    bucket = fake.storage.from_(AVATAR_BUCKET)
    assert bucket.uploaded == []
    assert bucket.removed == []
    assert report.applied is False
    assert report.shrunk == 1


def test_a_dry_run_still_says_what_it_would_save() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"))
    report = shrink_all(fake, apply=False)

    assert report.after_total < report.before_total / 4
    assert report.rows[0].before_bytes > report.rows[0].after_bytes > 0


def test_applying_stores_an_avatar_sized_jpeg_cached_for_a_year() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"))
    shrink_all(fake, apply=True)

    (path, data, options) = fake.storage.from_(AVATAR_BUCKET).uploaded[0]
    with Image.open(io.BytesIO(data)) as image:
        assert max(image.size) == 480
    assert options["cache-control"] == "31536000"
    assert path.startswith(ALICE) and path != f"{ALICE}.jpg"


def test_the_old_file_goes_only_after_the_member_points_at_the_new_one() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"))
    shrink_all(fake, apply=True)
    assert fake.storage.from_(AVATAR_BUCKET).removed == [[f"{ALICE}.jpg"]]


def test_a_second_run_does_nothing() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"))
    shrink_all(fake, apply=True)

    # The club now holds what the first run stored, under its own name.
    bucket = fake.storage.from_(AVATAR_BUCKET)
    (path, data, _) = bucket.uploaded[0]
    bucket.objects[path] = data
    fake.tables["players"][0]["avatar_url"] = f"{PUBLIC}/{path}"
    bucket.uploaded.clear()
    bucket.removed.clear()

    report = shrink_all(fake, apply=True)
    assert bucket.uploaded == []
    assert bucket.removed == []
    assert (report.shrunk, report.already, report.failed) == (0, 1, 0)


def test_a_member_with_no_photo_is_not_in_the_report() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=None), member(BOB, "ต้น", path=f"{BOB}.jpg"))
    report = shrink_all(fake, apply=False)
    assert [row.nickname for row in report.rows] == ["ต้น"]


def test_a_photo_missing_from_the_bucket_is_reported_and_the_rest_still_run() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"), member(BOB, "ต้น", path=f"{BOB}.jpg"))
    del fake.storage.from_(AVATAR_BUCKET).objects[f"{ALICE}.jpg"]

    report = shrink_all(fake, apply=True)
    assert (report.shrunk, report.failed) == (1, 1)
    by_name = {row.nickname: row for row in report.rows}
    assert by_name["กิ๊ก"].status == "failed"
    assert by_name["ต้น"].status == "shrunk"
    # The one that worked was still written.
    assert len(fake.storage.from_(AVATAR_BUCKET).uploaded) == 1


def test_a_stored_file_that_is_not_an_image_is_reported_not_stored() -> None:
    fake = club(member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg", data=b"not an image"))
    report = shrink_all(fake, apply=True)

    assert report.failed == 1
    assert fake.storage.from_(AVATAR_BUCKET).uploaded == []


def test_a_photo_hosted_somewhere_else_is_left_alone() -> None:
    fake = FakeSupabase(
        {
            "players": [
                {"id": ALICE, "nickname": "กิ๊ก", "avatar_url": "https://cdn.example.com/a.jpg"}
            ]
        }
    )
    report = shrink_all(fake, apply=True)

    assert report.failed == 1
    assert "not in this project's bucket" in (report.rows[0].detail or "")
    assert fake.storage.from_(AVATAR_BUCKET).uploaded == []


def test_the_totals_add_up_across_the_club() -> None:
    fake = club(
        member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg"),
        member(BOB, "ต้น", path=f"{BOB}.jpg", data=photo(1200, (20, 180, 90))),
    )
    report = shrink_all(fake, apply=False)

    assert report.before_total == sum(row.before_bytes for row in report.rows)
    assert report.after_total == sum(row.after_bytes for row in report.rows)
    assert report.shrunk == 2


def test_the_endpoint_needs_an_admin(client: Any, supabase_rows: dict[str, Any]) -> None:
    """Resizing every member's photo is not something a visitor may ask for."""
    supabase_rows["players"] = []
    assert client.post("/api/admin/players/avatars/shrink").status_code == 401


def test_the_endpoint_is_a_dry_run_unless_asked(
    client: Any, supabase_spy: FakeSupabase, supabase_rows: dict[str, Any]
) -> None:
    from uuid import uuid4

    from app.security import create_access_token

    supabase_rows["players"] = [member(ALICE, "กิ๊ก", path=f"{ALICE}.jpg")]
    bucket = supabase_spy.storage.from_(AVATAR_BUCKET)
    bucket.objects[f"{ALICE}.jpg"] = supabase_rows["players"][0].pop("_bytes")
    auth = {
        "Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"
    }

    body = client.post("/api/admin/players/avatars/shrink", headers=auth).json()
    assert body["applied"] is False
    assert body["shrunk"] == 1
    assert bucket.uploaded == []

    body = client.post("/api/admin/players/avatars/shrink?apply=true", headers=auth).json()
    assert body["applied"] is True
    assert len(bucket.uploaded) == 1
