"""A copy of the club's data an admin can download and keep.

Supabase's free plan keeps no daily backups, so this is the club's own: one
ZIP with every table twice over —

- ``data.json``: every row exactly as stored, for putting the data back;
- ``csv/<table>.csv``: the same rows for a person, opened in Excel or
  Google Sheets (UTF-8 with a byte-order mark, which is what makes Excel
  read Thai instead of mojibake).

Files in storage (slips, receipts, product photos, logos) stay out: they
would make the download hundreds of megabytes and cost the egress the free
plan is short of. Their URLs are in the rows, so nothing loses track of
them. Admins' password hashes stay out too — a backup is a file that gets
copied around, and a hash is the one thing in the database worth stealing.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from supabase import Client

from app.db_utils import rows

# In an order that can be put back one table after another: everything a
# row points at comes before it.
TABLES: list[tuple[str, str]] = [
    # (table, column to page through it by — a unique one, so no row is
    # read twice or skipped when one page ends mid-run of equal values)
    ("admins", "id"),
    ("club_settings", "id"),
    ("players", "id"),
    ("sessions", "id"),
    ("checkins", "id"),
    ("matches", "id"),
    ("pairing_history", "id"),
    ("locked_pairs", "id"),
    ("billings", "id"),
    ("expenses", "id"),
    ("other_income", "id"),
    ("sponsors", "id"),
    ("products", "id"),
    ("product_stock", "product_id,size"),
    ("shop_orders", "id"),
    ("shop_order_items", "id"),
    ("admin_activity_log", "id"),
    ("line_link_requests", "id"),
    ("line_join_requests", "id"),
]

# Columns never written to a backup, per table.
LEFT_OUT: dict[str, set[str]] = {"admins": {"password_hash"}}

# PostgREST hands back at most this many rows per request by default.
PAGE = 1000
# A ceiling, not an expectation: a club's tables are thousands of rows. It
# keeps a read that keeps returning full pages from running forever.
MAX_PAGES = 500


@dataclass(frozen=True)
class Backup:
    filename: str
    content: bytes
    counts: dict[str, int]

    @property
    def total_rows(self) -> int:
        return sum(self.counts.values())


def read_table(supabase: Client, table: str, order_by: str) -> list[dict[str, Any]]:
    """Every row of a table, a page at a time."""
    found: list[dict[str, Any]] = []
    for page_no in range(MAX_PAGES):
        start = page_no * PAGE
        query = supabase.table(table).select("*")
        for column in order_by.split(","):
            query = query.order(column)
        page = rows(query.range(start, start + PAGE - 1).execute())
        found.extend(page)
        # A short page is the last one. A page longer than asked for means
        # the range was not applied at all — everything came at once, and
        # asking again would only bring the same rows back forever.
        if len(page) != PAGE:
            return found
    raise RuntimeError(
        f"{table}: more than {MAX_PAGES * PAGE} rows — too big to back up in one request"
    )


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def to_csv(table_rows: list[dict[str, Any]]) -> bytes:
    columns = columns_of(table_rows)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(columns)
    for row in table_rows:
        writer.writerow([_cell(row.get(c)) for c in columns])
    return ("﻿" + out.getvalue()).encode("utf-8")


def _readme(stamp: str, counts: dict[str, int]) -> str:
    lines = [
        "ไฟล์สำรองข้อมูล นิดเดียว BMT",
        f"สร้างเมื่อ {stamp} (เวลาไทย)",
        "",
        "data.json    ข้อมูลทุกตารางแบบครบถ้วน ใช้กู้คืนข้อมูล",
        "csv/         ข้อมูลเดียวกัน เปิดด้วย Excel หรือ Google Sheets ได้",
        "",
        "ไม่รวม: รูปภาพ (สลิป ใบเสร็จ รูปสินค้า โลโก้ — มีแค่ลิงก์) และรหัสผ่านแอดมิน",
        "ไฟล์นี้มีชื่อและเบอร์โทรของลูกค้า เก็บไว้ในที่ปลอดภัย อย่าส่งต่อในกลุ่ม",
        "",
        "จำนวนแถว:",
    ]
    lines += [f"  {table:<20} {n}" for table, n in counts.items()]
    return "\n".join(lines) + "\n"


def collect(supabase: Client) -> dict[str, list[dict[str, Any]]]:
    """Every table's rows, minus the columns that never leave (LEFT_OUT)."""
    data: dict[str, list[dict[str, Any]]] = {}
    for table, order_by in TABLES:
        dropped = LEFT_OUT.get(table, set())
        data[table] = [
            {k: v for k, v in row.items() if k not in dropped}
            for row in read_table(supabase, table, order_by)
        ]
    return data


def columns_of(table_rows: list[dict[str, Any]]) -> list[str]:
    """Columns in the order the first row has them, then any a later row adds."""
    columns: list[str] = []
    for row in table_rows:
        columns.extend(c for c in row if c not in columns)
    return columns


def build_backup(supabase: Client, now: datetime) -> Backup:
    """``now`` in the club's time zone — it names the file and dates it."""
    data = collect(supabase)
    counts = {table: len(table_rows) for table, table_rows in data.items()}
    stamp = now.strftime("%Y-%m-%d %H:%M")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", _readme(stamp, counts))
        archive.writestr(
            "data.json",
            json.dumps(
                {"exported_at": now.isoformat(), "counts": counts, "tables": data},
                ensure_ascii=False,
                indent=1,
                default=str,
            ),
        )
        for table, table_rows in data.items():
            archive.writestr(f"csv/{table}.csv", to_csv(table_rows))
    return Backup(
        filename=f"niddeaw-backup-{now.strftime('%Y-%m-%d-%H%M')}.zip",
        content=buffer.getvalue(),
        counts=counts,
    )
