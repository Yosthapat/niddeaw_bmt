"""The admin's backup download: everything in it, nothing it must not hold."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.middleware.activity_log as activity_log_mw
from app.security import create_access_token
from app.services import backup_service
from app.services.shop_service import CLUB_TZ
from tests.conftest import FakeResult, FakeSupabase

ADMIN_ID = str(uuid4())


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=ADMIN_ID, role='admin')}"}


def open_zip(content: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(content))


def test_a_backup_needs_an_admin(client: TestClient, supabase_rows: dict[str, Any]) -> None:
    assert client.post("/api/admin/backup").status_code == 401
    assert client.get("/api/admin/backup/last").status_code == 401


def test_the_backup_holds_every_table_as_json_and_csv(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [
        {"id": ADMIN_ID, "username": "Vaan", "password_hash": "$2b$12$secret", "role": "admin"}
    ]
    supabase_rows["players"] = [{"id": "p1", "nickname": "ปุ๊กปิ๊ก", "is_active": True, "elo": 1012.5}]
    supabase_rows["shop_orders"] = [
        {
            "id": "o1",
            "order_no": 12,
            "player_id": None,
            "guest_name": "พี่ต้น",
            "guest_phone": "0812345678",
        }
    ]
    supabase_rows["admin_activity_log"] = [{"id": "l1", "detail": {"items": ["เสื้อ M × 2"]}}]

    response = client.post("/api/admin/backup", headers=auth())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="niddeaw-backup-'
    )
    archive = open_zip(response.content)
    names = set(archive.namelist())
    assert {"README.txt", "data.json"} <= names
    assert {f"csv/{table}.csv" for table, _ in backup_service.TABLES} <= names

    data = json.loads(archive.read("data.json"))
    assert set(data["tables"]) == {table for table, _ in backup_service.TABLES}
    assert data["tables"]["players"] == supabase_rows["players"]
    assert data["tables"]["shop_orders"][0]["guest_phone"] == "0812345678"
    assert data["counts"]["players"] == 1 and data["counts"]["sessions"] == 0


def test_admin_password_hashes_never_leave(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [
        {"id": ADMIN_ID, "username": "Vaan", "password_hash": "$2b$12$secret"}
    ]
    archive = open_zip(client.post("/api/admin/backup", headers=auth()).content)
    for name in archive.namelist():
        assert b"$2b$12$secret" not in archive.read(name), name
        assert b"password_hash" not in archive.read(name), name
    assert json.loads(archive.read("data.json"))["tables"]["admins"] == [
        {"id": ADMIN_ID, "username": "Vaan"}
    ]


def test_the_csv_opens_in_excel_with_thai_intact() -> None:
    content = backup_service.to_csv(
        [
            {
                "nickname": "ปุ๊กปิ๊ก",
                "is_active": True,
                "note": None,
                "detail": {"items": ["เสื้อ M × 2"]},
            },
            {"nickname": "Ball, Jr.", "is_active": False, "added_later": 3},
        ]
    )
    # The byte-order mark is what makes Excel read UTF-8 rather than guess.
    assert content.startswith("﻿".encode())
    table = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    assert table[0] == ["nickname", "is_active", "note", "detail", "added_later"]
    assert table[1] == ["ปุ๊กปิ๊ก", "true", "", '{"items": ["เสื้อ M × 2"]}', ""]
    assert table[2] == ["Ball, Jr.", "false", "", "", "3"]


class Paged:
    """A table that honours .range(), as PostgREST's row cap makes it matter."""

    def __init__(self, n: int) -> None:
        self.all = [{"id": f"{i:05d}"} for i in range(n)]
        self.ranges: list[tuple[int, int]] = []
        self.orders: list[str] = []

    def table(self, _: str) -> Paged:
        return self

    def select(self, *_: Any) -> Paged:
        return self

    def order(self, column: str) -> Paged:
        self.orders.append(column)
        return self

    def range(self, start: int, end: int) -> Paged:
        self.ranges.append((start, end))
        self._page = self.all[start : end + 1]
        return self

    def execute(self) -> FakeResult:
        return FakeResult(self._page)


@pytest.mark.parametrize("n", [0, 999, 1000, 2500])
def test_a_big_table_is_read_a_page_at_a_time(n: int) -> None:
    db = Paged(n)
    found = backup_service.read_table(db, "matches", "id")  # type: ignore[arg-type]
    assert found == db.all
    assert db.ranges[0] == (0, 999)
    assert set(db.orders) == {"id"}


def test_a_two_column_key_orders_by_both() -> None:
    db = Paged(3)
    backup_service.read_table(db, "product_stock", "product_id,size")  # type: ignore[arg-type]
    assert db.orders == ["product_id", "size"]


def test_the_file_is_named_for_the_club_day() -> None:
    backup = backup_service.build_backup(
        FakeSupabase(), datetime(2026, 11, 2, 21, 40, tzinfo=CLUB_TZ)
    )  # type: ignore[arg-type]
    assert backup.filename == "niddeaw-backup-2026-11-02-2140.zip"
    readme = open_zip(backup.content).read("README.txt").decode()
    assert "2026-11-02 21:40" in readme and "รหัสผ่านแอดมิน" in readme


def test_the_download_is_logged_with_its_size(
    client: TestClient,
    supabase_rows: dict[str, list[dict[str, Any]]],
    supabase_spy: FakeSupabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase_rows["players"] = [{"id": "p1"}, {"id": "p2"}]
    monkeypatch.setattr(activity_log_mw, "get_supabase_client", lambda: supabase_spy)
    client.post("/api/admin/backup", headers=auth())
    inserts = [args[0] for name, args, _ in supabase_spy.calls if name == "insert"]
    assert len(inserts) == 1
    entry = inserts[0]
    assert entry["action"] == "ดาวน์โหลดไฟล์สำรองข้อมูล"
    assert entry["path"] == "/api/admin/backup"
    assert entry["detail"] == {"tables": len(backup_service.TABLES), "rows": 2}


def test_last_backup_when_there_has_been_none(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    response = client.get("/api/admin/backup/last", headers=auth())
    assert response.status_code == 200
    assert response.json() == {"at": None, "by": None, "rows": None}


def test_last_backup_says_when_and_who(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]], supabase_spy: FakeSupabase
) -> None:
    supabase_rows["admin_activity_log"] = [
        {
            "admin_id": ADMIN_ID,
            "detail": {"tables": 17, "rows": 1234},
            "created_at": "2026-11-02T14:40:00+00:00",
        }
    ]
    supabase_rows["admins"] = [{"username": "Vaan"}]
    body = client.get("/api/admin/backup/last", headers=auth()).json()
    assert body["by"] == "Vaan" and body["rows"] == 1234
    assert body["at"].startswith("2026-11-02T14:40:00")
    # Read from the log entries of this one endpoint, newest first.
    assert ("eq", ("path", "/api/admin/backup"), {}) in supabase_spy.calls
    assert ("order", ("created_at",), {"desc": True}) in supabase_spy.calls


def test_a_source_that_ignores_the_range_cannot_loop_forever() -> None:
    class Stuck(Paged):
        def range(self, start: int, end: int) -> Paged:
            self.ranges.append((start, end))
            self._page = self.all[:1000]  # the same full page every time
            return self

    db = Stuck(1000)
    with pytest.raises(RuntimeError, match="too big"):
        backup_service.read_table(db, "matches", "id")  # type: ignore[arg-type]
    assert len(db.ranges) == backup_service.MAX_PAGES
