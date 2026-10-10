"""The one-off that rewrites every avatar already in the bucket.

This script is run by hand against the real club's data, so the things
worth pinning down are the ones that would be expensive to get wrong: that
a dry run writes nothing, that a second run is a no-op, and that the old
file is only deleted once the player points at the new one.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
from typing import Any

import pytest
from PIL import Image

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tools")
spec = importlib.util.spec_from_file_location(
    "shrink_avatars", os.path.join(TOOLS, "shrink_avatars.py")
)
assert spec and spec.loader
shrink_avatars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shrink_avatars)

PLAYER_ID = "11111111-1111-1111-1111-111111111111"
PUBLIC = "https://fake.supabase.co/storage/v1/object/public/avatars"


def photo(size: int = 1600) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (size, size), (200, 30, 90)).save(out, format="JPEG", quality=95)
    return out.getvalue()


class FakeBucket:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes, dict[str, str]]] = []
        self.removed: list[list[str]] = []

    def upload(self, path: str, data: bytes, options: dict[str, str]) -> None:
        self.uploaded.append((path, data, options))

    def get_public_url(self, path: str) -> str:
        return f"{PUBLIC}/{path}"

    def remove(self, paths: list[str]) -> None:
        self.removed.append(paths)


class FakeTable:
    def __init__(self, parent: "FakeClient", rows: list[dict[str, Any]]) -> None:
        self.parent = parent
        self._rows = rows
        self._update: dict[str, Any] | None = None

    def select(self, *_: Any) -> "FakeTable":
        return self

    def update(self, values: dict[str, Any]) -> "FakeTable":
        self._update = values
        return self

    def eq(self, _column: str, value: Any) -> "FakeTable":
        if self._update is not None:
            self.parent.updates.append((value, self._update))
        return self

    def execute(self) -> Any:
        return type("R", (), {"data": self._rows})()


class FakeStorage:
    def __init__(self, bucket: FakeBucket) -> None:
        self.bucket = bucket

    def from_(self, _name: str) -> FakeBucket:
        return self.bucket


class FakeClient:
    def __init__(self, rows: list[dict[str, Any]], bucket: FakeBucket) -> None:
        self.rows = rows
        self.storage = FakeStorage(bucket)
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def table(self, _name: str) -> FakeTable:
        return FakeTable(self, self.rows)


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch) -> Any:
    """A bucket holding one 1600px photo, and the knobs to run against it."""
    stored = photo()
    bucket = FakeBucket()
    rows = [{"id": PLAYER_ID, "nickname": "กิ๊ก", "avatar_url": f"{PUBLIC}/{PLAYER_ID}.jpg"}]
    client = FakeClient(rows, bucket)

    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-not-a-real-key")
    import supabase as supabase_module

    monkeypatch.setattr(supabase_module, "create_client", lambda *_a, **_k: client)

    class Response:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self) -> bytes:
            return self.data

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(
        shrink_avatars.urllib.request, "urlopen", lambda *_a, **_k: Response(stored)
    )
    return type("Lab", (), {"client": client, "bucket": bucket, "rows": rows, "original": stored})()


def run(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "argv", ["shrink_avatars.py", *argv])
    return shrink_avatars.main()


def test_a_dry_run_writes_nothing(lab: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run([], monkeypatch) == 0
    assert lab.bucket.uploaded == []
    assert lab.bucket.removed == []
    assert lab.client.updates == []


def test_applying_stores_a_smaller_photo_under_a_new_name(
    lab: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert run(["--apply"], monkeypatch) == 0
    (path, data, options) = lab.bucket.uploaded[0]
    with Image.open(io.BytesIO(data)) as image:
        assert max(image.size) == 480
    assert len(data) < len(lab.original) / 4
    assert path != f"{PLAYER_ID}.jpg"
    assert options["cache-control"] == "31536000"


def test_the_player_is_pointed_at_the_new_file(lab: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    run(["--apply"], monkeypatch)
    (player_id, values) = lab.client.updates[0]
    assert player_id == PLAYER_ID
    assert values["avatar_url"] == f"{PUBLIC}/{lab.bucket.uploaded[0][0]}"


def test_the_old_file_is_deleted(lab: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    run(["--apply"], monkeypatch)
    assert lab.bucket.removed == [[f"{PLAYER_ID}.jpg"]]


def test_running_it_twice_does_nothing_the_second_time(
    lab: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    run(["--apply"], monkeypatch)
    # The club's row now points at the shrunk file, which is what a second
    # run would download.
    shrunk = lab.bucket.uploaded[0][1]
    lab.rows[0]["avatar_url"] = lab.client.updates[0][1]["avatar_url"]
    monkeypatch.setattr(
        shrink_avatars.urllib.request,
        "urlopen",
        lambda *_a, **_k: type(
            "R",
            (),
            {
                "read": lambda self: shrunk,
                "__enter__": lambda self: self,
                "__exit__": lambda self, *a: None,
            },
        )(),
    )
    lab.bucket.uploaded.clear()
    lab.bucket.removed.clear()
    lab.client.updates.clear()

    assert run(["--apply"], monkeypatch) == 0
    assert lab.bucket.uploaded == []
    assert lab.bucket.removed == []
    assert lab.client.updates == []


def test_one_broken_photo_does_not_stop_the_others(
    lab: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab.rows.append(
        {"id": "22222222-2222-2222-2222-222222222222", "nickname": "ต้น", "avatar_url": None}
    )
    calls = {"n": 0}

    def flaky(*_a: object, **_k: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("404 while fetching")
        raise AssertionError("only one member has a photo")

    monkeypatch.setattr(shrink_avatars.urllib.request, "urlopen", flaky)
    # A failure is reported in the exit code, and nothing was written.
    assert run(["--apply"], monkeypatch) == 1
    assert lab.bucket.uploaded == []
