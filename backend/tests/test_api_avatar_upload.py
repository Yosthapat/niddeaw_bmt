"""The avatar endpoint, judged by what it leaves in the bucket.

Every member's photo is sent to every visitor of the members, ranking and
live pages, so what this endpoint stores is the club's bandwidth bill. The
response body says nothing about that; these read the bucket instead.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.security import create_access_token
from app.services.image_service import AVATAR_MAX_PX
from tests.conftest import FakeSupabase

PLAYER_ID = "11111111-1111-1111-1111-111111111111"


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def photo(width: int = 1600, height: int = 1600) -> bytes:
    image = Image.new("RGB", (width, height), (200, 30, 90))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=95)
    return out.getvalue()


def player_row(avatar_url: str | None = None) -> dict[str, Any]:
    return {
        "id": PLAYER_ID,
        "nickname": "กิ๊ก",
        "member_seq": 1,
        "avatar_url": avatar_url,
        "elo_score": 1200,
        "elo_level": "highball",
        "is_active": True,
        "line_id": None,
        "dominant_hand": None,
        "tiktok": None,
        "instagram": None,
        "quote": None,
        "created_at": "2026-10-01T10:00:00+00:00",
    }


@pytest.fixture
def players(supabase_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    supabase_rows["players"] = [player_row()]
    return supabase_rows["players"]


def upload(client: TestClient, data: bytes, filename: str = "photo.jpg") -> Any:
    return client.post(
        f"/api/admin/players/{PLAYER_ID}/avatar",
        files={"file": (filename, data, "image/jpeg")},
        headers=auth(),
    )


def test_what_lands_in_the_bucket_is_the_size_the_site_draws(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    original = photo()
    assert upload(client, original).status_code == 200

    (path, stored, options) = supabase_spy.storage.from_("avatars").uploaded[0]
    with Image.open(io.BytesIO(stored)) as image:
        assert max(image.size) == AVATAR_MAX_PX
    assert len(stored) < len(original) / 4
    assert path.startswith(PLAYER_ID) and path.endswith(".jpg")
    assert options["content-type"] == "image/jpeg"


def test_it_is_cached_for_a_year(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    upload(client, photo())
    (_, _, options) = supabase_spy.storage.from_("avatars").uploaded[0]
    assert options["cache-control"] == "31536000"


def test_a_new_photo_gets_a_new_url_so_the_year_long_cache_is_safe(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    upload(client, photo())
    first = supabase_spy.storage.from_("avatars").uploaded[0][0]

    # The admin picks a different photo for the same player.
    players[0]["avatar_url"] = (
        f"https://fake.supabase.co/storage/v1/object/public/avatars/{first}"
    )
    upload(client, photo(1200, 800))
    second = supabase_spy.storage.from_("avatars").uploaded[1][0]

    assert first != second


def test_the_photo_it_replaces_is_deleted(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    stale = f"{PLAYER_ID}-oldoldoldol.jpg"
    players[0]["avatar_url"] = (
        f"https://fake.supabase.co/storage/v1/object/public/avatars/{stale}"
    )
    upload(client, photo())
    assert supabase_spy.storage.from_("avatars").removed == [[stale]]


def test_a_player_with_no_photo_yet_deletes_nothing(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    upload(client, photo())
    assert supabase_spy.storage.from_("avatars").removed == []


def test_re_uploading_the_same_photo_does_not_delete_the_file_it_just_wrote(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    same = photo()
    upload(client, same)
    path = supabase_spy.storage.from_("avatars").uploaded[0][0]
    players[0]["avatar_url"] = (
        f"https://fake.supabase.co/storage/v1/object/public/avatars/{path}"
    )

    upload(client, same)
    assert supabase_spy.storage.from_("avatars").removed == []


def test_a_file_that_is_not_an_image_is_refused_rather_than_stored(
    client: TestClient, supabase_spy: FakeSupabase, players: list[dict[str, Any]]
) -> None:
    response = upload(client, b"not a photo at all", filename="photo.jpg")
    assert response.status_code == 400
    assert supabase_spy.storage.from_("avatars").uploaded == []


def test_an_unknown_player_is_a_404_and_stores_nothing(
    client: TestClient, supabase_spy: FakeSupabase, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["players"] = []
    assert upload(client, photo()).status_code == 404
    assert supabase_spy.storage.from_("avatars").uploaded == []
