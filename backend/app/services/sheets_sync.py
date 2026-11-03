"""Copies the club's data into its Google Sheet.

The sheet holds three kinds of tab:

- one per table, Thai-named ("สมาชิก", "แมตช์", …), replaced on every sync:
  the club as it is now, to read, filter or do the accounts from;
- "สำรอง YYYY-MM-DD", one per sync day, every table stacked down the
  page. The last ``KEEP_SNAPSHOTS`` stay; a sync never writes over an older
  one, so data that went wrong this week cannot wipe out last week's;
- "ประวัติซิงก์", a line per sync: when, by whom, how many rows.

The ZIP download stays the backup to restore from; the sheet is the copy
that is always there to look at without remembering to press anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from supabase import Client

from app.services.backup_service import TABLES, collect, columns_of
from app.services.google_sheets import a1

LOG_TAB = "ประวัติซิงก์"
LOG_HEADER = ["เวลา (ไทย)", "ซิงก์โดย", "จำนวนแถว", "แท็บสำรอง"]
SNAPSHOT_PREFIX = "สำรอง "
KEEP_SNAPSHOTS = 8
# Google refuses a cell longer than this.
MAX_CELL = 50_000

TAB_TITLES: dict[str, str] = {
    "admins": "แอดมิน",
    "club_settings": "ตั้งค่าก๊วน",
    "players": "สมาชิก",
    "sessions": "รอบเล่น",
    "checkins": "เช็คอิน",
    "matches": "แมตช์",
    "pairing_history": "ประวัติจับคู่",
    "locked_pairs": "คู่ล็อค",
    "billings": "บิลผู้เล่น",
    "expenses": "รายจ่าย",
    "other_income": "รายรับอื่น",
    "sponsors": "ผู้สนับสนุน",
    "products": "สินค้า",
    "product_stock": "สต็อกสินค้า",
    "shop_orders": "ออเดอร์",
    "shop_order_items": "รายการในออเดอร์",
    "admin_activity_log": "ประวัติแอดมิน",
    "line_link_requests": "คำขอผูก LINE",
}
assert set(TAB_TITLES) == {table for table, _ in TABLES}, "every backed-up table needs a tab"

EMPTY = "ยังไม่มีข้อมูล"


class Api(Protocol):
    """What the sync needs from SheetsApi — a fake stands in for it in tests."""

    @property
    def url(self) -> str: ...
    def tabs(self) -> dict[str, int]: ...
    def batch_update(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
    def clear(self, ranges: list[str]) -> None: ...
    def write(self, data: list[tuple[str, list[list[Any]]]]) -> None: ...
    def append(self, range_: str, values: list[list[Any]]) -> None: ...
    def read(self, range_: str) -> list[list[Any]]: ...


@dataclass(frozen=True)
class SyncResult:
    at: str
    rows: int
    snapshot: str
    removed_snapshots: list[str]
    url: str


def cell(value: Any) -> Any:
    """A value as Sheets stores it: numbers and true/false stay themselves,
    so a total can still be summed; everything else becomes text."""
    if value is None:
        return ""
    if isinstance(value, (bool, int, float)):
        return value
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + "…"


def grid(table_rows: list[dict[str, Any]]) -> list[list[Any]]:
    """Header and rows for one table's tab."""
    columns = columns_of(table_rows)
    if not columns:
        return [[EMPTY]]
    return [columns] + [[cell(row.get(c)) for c in columns] for row in table_rows]


def snapshot_grid(data: dict[str, list[dict[str, Any]]]) -> list[list[Any]]:
    out: list[list[Any]] = []
    for table, table_rows in data.items():
        out.append([f"■ {TAB_TITLES[table]} ({table}) — {len(table_rows)} แถว"])
        out.extend(grid(table_rows) if table_rows else [])
        out.append([])
    return out


def _width(values: list[list[Any]]) -> int:
    return max((len(r) for r in values), default=1) or 1


def _size(sheet_id: int, values: list[list[Any]], *, frozen: int) -> dict[str, Any]:
    """Fits a tab's grid to what is about to be written: room for every row
    (a tab starts at 1000), and none of last week's rows left below it.
    At least two rows, because Sheets will not freeze a tab's only row."""
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "rowCount": max(len(values), 2),
                    "columnCount": _width(values),
                    "frozenRowCount": frozen,
                },
            },
            "fields": "gridProperties(rowCount,columnCount,frozenRowCount)",
        }
    }


def sync(supabase: Client, api: Api, now: datetime, who: str) -> SyncResult:
    """``now`` in the club's time zone."""
    data = collect(supabase)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    snapshot = SNAPSHOT_PREFIX + now.strftime("%Y-%m-%d")

    latest = {TAB_TITLES[table]: grid(table_rows) for table, table_rows in data.items()}
    stacked = snapshot_grid(data)

    tabs = api.tabs()
    wanted = [LOG_TAB, *latest, snapshot]
    missing = [title for title in wanted if title not in tabs]
    replies = api.batch_update(
        [
            # The log first and the tables in a fixed order, so a new sheet
            # reads the same as the club's own pages; snapshots go last.
            {"addSheet": {"properties": {"title": title, "index": wanted.index(title)}}}
            for title in missing
            if title != snapshot
        ]
        + ([{"addSheet": {"properties": {"title": snapshot}}}] if snapshot in missing else [])
    )
    added = [r["addSheet"]["properties"] for r in replies if "addSheet" in r]
    tabs.update({p["title"]: int(p["sheetId"]) for p in added})

    snapshots = sorted(t for t in tabs if t.startswith(SNAPSHOT_PREFIX))
    too_old = snapshots[:-KEEP_SNAPSHOTS] if len(snapshots) > KEEP_SNAPSHOTS else []

    api.batch_update(
        [_size(tabs[title], values, frozen=1) for title, values in latest.items()]
        + [_size(tabs[snapshot], stacked, frozen=0)]
        + [{"deleteSheet": {"sheetId": tabs[title]}} for title in too_old]
    )
    api.clear([a1(title) for title in [*latest, snapshot]])
    writes: list[tuple[str, list[list[Any]]]] = [
        (a1(title, "A1"), values) for title, values in latest.items()
    ]
    writes.append((a1(snapshot, "A1"), stacked))
    if LOG_TAB in missing:
        writes.append((a1(LOG_TAB, "A1"), [LOG_HEADER]))
    api.write(writes)

    total = sum(len(table_rows) for table_rows in data.values())
    api.append(a1(LOG_TAB, "A:D"), [[stamp, who, total, snapshot]])
    return SyncResult(
        at=stamp, rows=total, snapshot=snapshot, removed_snapshots=too_old, url=api.url
    )


def last_sync(api: Api) -> list[Any] | None:
    """The newest line of the sheet's own log, or None before the first."""
    lines = api.read(a1(LOG_TAB, "A:D"))
    return lines[-1] if len(lines) > 1 else None
