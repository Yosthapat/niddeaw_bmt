"""Sponsors, from the file a sponsor sends to the logo on the home band.

The band shows every logo as the same white silhouette. An admin adds a
sponsor from a phone with whatever file they were given, so the endpoint
has to make that silhouette itself — these check the pixels it stores,
not just the response.
"""

from __future__ import annotations

import base64
import io
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.security import create_access_token
from app.services.logo_service import LOGO_MAX_PX, white_silhouette
from tests.conftest import FakeSupabase

SPONSOR_ID = "22222222-2222-2222-2222-222222222222"


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def logo_on_white(width: int = 900, height: int = 300) -> bytes:
    """A dark wordmark on a white JPG — the usual thing a sponsor sends."""
    image = Image.new("RGB", (width, height), (255, 255, 255))
    for x in range(200, 600):
        for y in range(100, 200):
            image.putpixel((x, y), (20, 20, 20))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90)
    return out.getvalue()


def sponsor_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": SPONSOR_ID, "name": "Wasteland", "href": "https://www.instagram.com/wastelandbkk",
        "logo_url": "/sponsors/wasteland-mono.png", "logo_width": 424, "logo_height": 104,
        "sort_order": 1, "is_visible": True, "created_at": "2026-10-28T00:00:00Z",
    }
    return {**row, **overrides}


def test_a_logo_on_a_white_background_becomes_a_trimmed_white_silhouette() -> None:
    logo = white_silhouette(logo_on_white())
    image = Image.open(io.BytesIO(logo.png))
    assert image.mode == "RGBA"
    # trimmed to the dark block, not the whole 900x300 picture
    assert (logo.width, logo.height) == (400, 100)
    r, g, b, a = image.getpixel((250, 50))
    assert (r, g, b, a) == (255, 255, 255, 255)


def test_a_transparent_png_keeps_its_own_cut_out() -> None:
    image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    for x in range(100, 300):
        for y in range(150, 250):
            image.putpixel((x, y), (40, 160, 220, 255))
    out = io.BytesIO()
    image.save(out, format="PNG")
    logo = white_silhouette(out.getvalue())
    assert (logo.width, logo.height) == (200, 100)


def test_a_huge_logo_is_shrunk_to_what_the_band_draws() -> None:
    logo = white_silhouette(logo_on_white(4000, 1000))
    assert max(logo.width, logo.height) <= LOGO_MAX_PX


def test_preview_shows_the_silhouette_and_stores_nothing(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    response = client.post(
        "/api/admin/sponsors/logo-preview",
        files={"file": ("logo.jpg", logo_on_white(), "image/jpeg")},
        headers=auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data_uri"].startswith("data:image/png;base64,")
    png = base64.b64decode(body["data_uri"].split(",", 1)[1])
    assert Image.open(io.BytesIO(png)).size == (body["width"], body["height"])
    assert supabase_spy.storage.buckets == {} or not supabase_spy.storage.from_("sponsors").uploaded


def test_a_blank_picture_is_refused_with_a_reason(client: TestClient, supabase_rows: dict[str, Any]) -> None:
    blank = io.BytesIO()
    Image.new("RGB", (300, 300), (255, 255, 255)).save(blank, format="PNG")
    response = client.post(
        "/api/admin/sponsors/logo-preview",
        files={"file": ("blank.png", blank.getvalue(), "image/png")},
        headers=auth(),
    )
    assert response.status_code == 400
    assert "ไม่เห็นโลโก้" in response.json()["detail"]


def test_adding_a_sponsor_stores_the_white_logo_and_puts_it_last(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    supabase_spy.tables["sponsors"] = [sponsor_row(sort_order=5)]
    response = client.post(
        "/api/admin/sponsors",
        data={"name": "  Match Mellow  ", "href": "@match.mellowww"},
        files={"file": ("logo.jpg", logo_on_white(), "image/jpeg")},
        headers=auth(),
    )
    assert response.status_code == 201
    inserts = [args[0] for name, args, _ in supabase_spy.calls if name == "insert"]
    assert inserts[0]["name"] == "Match Mellow"
    assert inserts[0]["href"] == "https://www.instagram.com/match.mellowww"
    assert inserts[0]["sort_order"] == 6
    assert (inserts[0]["logo_width"], inserts[0]["logo_height"]) == (400, 100)
    path, data, options = supabase_spy.storage.from_("sponsors").uploaded[0]
    assert path.endswith(".png") and options["content-type"] == "image/png"
    assert inserts[0]["logo_url"].endswith(path)
    assert Image.open(io.BytesIO(data)).getpixel((250, 50)) == (255, 255, 255, 255)


@pytest.mark.parametrize("href", ["hello world", "javascript:alert(1)"])
def test_a_link_that_is_not_a_link_is_refused(
    client: TestClient, supabase_spy: FakeSupabase, href: str
) -> None:
    response = client.post(
        "/api/admin/sponsors",
        data={"name": "X", "href": href},
        files={"file": ("logo.jpg", logo_on_white(), "image/jpeg")},
        headers=auth(),
    )
    assert response.status_code == 400
    assert "Instagram" in response.json()["detail"]
    assert not supabase_spy.storage.from_("sponsors").uploaded


def test_a_sponsor_needs_a_name(client: TestClient, supabase_spy: FakeSupabase) -> None:
    response = client.post(
        "/api/admin/sponsors",
        data={"name": "   "},
        files={"file": ("logo.jpg", logo_on_white(), "image/jpeg")},
        headers=auth(),
    )
    assert response.status_code == 400


def test_the_home_band_asks_only_for_visible_sponsors_in_order(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    supabase_spy.tables["sponsors"] = [sponsor_row()]
    response = client.get("/api/sponsors")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Wasteland"
    assert ("eq", ("is_visible", True), {}) in supabase_spy.calls
    assert ("order", ("sort_order",), {}) in supabase_spy.calls


def test_hiding_a_sponsor_is_an_update_not_a_delete(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    supabase_spy.tables["sponsors"] = [sponsor_row(is_visible=False)]
    response = client.patch(f"/api/admin/sponsors/{SPONSOR_ID}", json={"is_visible": False}, headers=auth())
    assert response.status_code == 200
    assert ("update", ({"is_visible": False},), {}) in supabase_spy.calls


def test_deleting_an_uploaded_logo_removes_its_file_but_never_a_shipped_one(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    uploaded = "https://fake.supabase.co/storage/v1/object/public/sponsors/abc123.png"
    supabase_spy.tables["sponsors"] = [sponsor_row(logo_url=uploaded)]
    assert client.delete(f"/api/admin/sponsors/{SPONSOR_ID}", headers=auth()).status_code == 204
    assert supabase_spy.storage.from_("sponsors").removed == [["abc123.png"]]

    supabase_spy.tables["sponsors"] = [sponsor_row()]  # /sponsors/wasteland-mono.png
    assert client.delete(f"/api/admin/sponsors/{SPONSOR_ID}", headers=auth()).status_code == 204
    assert supabase_spy.storage.from_("sponsors").removed == [["abc123.png"]]


def test_reordering_numbers_them_in_the_order_given(
    client: TestClient, supabase_spy: FakeSupabase
) -> None:
    first, second = str(uuid4()), str(uuid4())
    supabase_spy.tables["sponsors"] = [sponsor_row()]
    response = client.put("/api/admin/sponsors/order", json={"ids": [second, first]}, headers=auth())
    assert response.status_code == 200
    updates = [args[0] for name, args, _ in supabase_spy.calls if name == "update"]
    assert updates == [{"sort_order": 1}, {"sort_order": 2}]
    eqs = [args for name, args, _ in supabase_spy.calls if name == "eq"]
    assert eqs[:2] == [("id", second), ("id", first)]


def test_only_an_admin_can_change_sponsors(client: TestClient, supabase_rows: dict[str, Any]) -> None:
    assert client.delete(f"/api/admin/sponsors/{SPONSOR_ID}").status_code == 401
