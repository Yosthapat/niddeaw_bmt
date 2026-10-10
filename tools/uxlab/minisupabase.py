"""A small in-memory stand-in for supabase-py's PostgREST client.

Used by lab.py to run the real FastAPI app with no Supabase project and no
network, so the UI can be driven end to end — see tools/uxlab/README.md.

Enough of the builder to run the real FastAPI app against: filters are
actually applied, inserts/updates/deletes actually mutate, column
projection is honoured (so a router that reads a column it forgot to
select fails here the way it would against the real API), and
`matches_numbered` is computed the way db/migrations/0025 defines it.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

Row = dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Columns each table fills in itself, as the schema's defaults do.
AUTO: dict[str, dict[str, Callable[[], Any]]] = {
    "players": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "sessions": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "checkins": {"id": lambda: str(uuid.uuid4()), "checkin_time": _now},
    "matches": {"id": lambda: str(uuid.uuid4()), "created_at": _now, "updated_at": _now},
    "billings": {"id": lambda: str(uuid.uuid4()), "updated_at": _now},
    "expenses": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "other_income": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "locked_pairs": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "pairing_history": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
    "admin_activity_log": {"id": lambda: str(uuid.uuid4()), "created_at": _now},
}

# Column defaults applied on insert when the caller omits them, mirroring
# the schema so a row inserted here validates like one from Postgres.
DEFAULTS: dict[str, Row] = {
    "players": {
        "avatar_url": None, "elo_score": 1000, "elo_level": "soju", "line_id": None,
        "is_active": True, "dominant_hand": None, "tiktok": None, "instagram": None,
        "quote": None, "games": 0, "wins": 0, "draws": 0, "losses": 0,
    },
    "sessions": {"status": "open", "shuttlecock_price_per_game": 0},
    "checkins": {"checkout_time": None},
    "matches": {
        "sets": None, "winner": None, "status": "in_progress", "court": None,
        "elo_delta_team1": None, "elo_delta_team2": None,
    },
    "billings": {"amount_adjusted": None, "paid_status": "unpaid", "promptpay_ref": None,
                 "game_count": 0},
    "expenses": {"receipt_url": None, "is_paid": False, "paid_at": None, "note": None},
    "other_income": {"slip_url": None, "note": None},
    "admin_activity_log": {"detail": None},
}


class Result:
    def __init__(self, data: list[Row], count: int | None = None) -> None:
        self.data = data
        self.count = len(data) if count is None else count


def _project(row: Row, columns: str | None) -> Row:
    if not columns or columns.strip() == "*":
        return dict(row)
    wanted = [c.strip() for c in columns.split(",") if c.strip()]
    if "*" in wanted:
        return dict(row)
    # A column the caller did not ask for is simply absent, exactly as
    # PostgREST returns it — that is what makes a forgotten column show up.
    return {c: row.get(c) for c in wanted}


def _parse_or(expr: str) -> Callable[[Row], bool]:
    """`or_("a.cs.{x},b.cs.{x}")` — only the handful of operators the app uses."""
    parts = re.findall(r"[^,]+\.[a-z_]+\.(?:\{[^}]*\}|[^,]*)", expr)
    preds: list[Callable[[Row], bool]] = []
    for part in parts:
        col, op, value = part.split(".", 2)
        if op == "cs":                       # array contains
            needle = value.strip("{}")
            preds.append(lambda r, c=col, n=needle: n in (r.get(c) or []))
        elif op == "eq":
            preds.append(lambda r, c=col, v=value: str(r.get(c)) == v)
        elif op == "is":
            preds.append(lambda r, c=col: r.get(c) is None)
        else:  # pragma: no cover - shows up loudly if the app grows one
            raise NotImplementedError(f"or_ operator {op!r}")
    return lambda row: any(p(row) for p in preds)


class Query:
    def __init__(self, db: "MiniSupabase", table: str) -> None:
        self._db = db
        self._table = table
        self._filters: list[Callable[[Row], bool]] = []
        self._columns: str | None = None
        self._count: Any = None
        self._head = False
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None
        self._op = "select"
        self._payload: Any = None
        self._on_conflict: str | None = None

    # builders
    def select(self, columns: str = "*", count: Any = None, head: bool = False) -> "Query":
        if self._op == "select":
            self._columns = columns
        self._count, self._head = count, head
        return self

    def insert(self, payload: Any) -> "Query":
        self._op, self._payload = "insert", payload
        return self

    def update(self, payload: Row) -> "Query":
        self._op, self._payload = "update", payload
        return self

    def upsert(self, payload: Any, on_conflict: str | None = None) -> "Query":
        self._op, self._payload, self._on_conflict = "upsert", payload, on_conflict
        return self

    def delete(self) -> "Query":
        self._op = "delete"
        return self

    def eq(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: str(r.get(column)) == str(value))
        return self

    def neq(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: str(r.get(column)) != str(value))
        return self

    def in_(self, column: str, values: list[Any]) -> "Query":
        wanted = {str(v) for v in values}
        self._filters.append(lambda r: str(r.get(column)) in wanted)
        return self

    def gt(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: r.get(column) is not None and str(r[column]) > str(value))
        return self

    def gte(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: r.get(column) is not None and str(r[column]) >= str(value))
        return self

    def lt(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: r.get(column) is not None and str(r[column]) < str(value))
        return self

    def lte(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda r: r.get(column) is not None and str(r[column]) <= str(value))
        return self

    def is_(self, column: str, value: str) -> "Query":
        if value != "null":  # pragma: no cover
            raise NotImplementedError(f"is_ {value!r}")
        self._filters.append(lambda r: r.get(column) is None)
        return self

    def or_(self, expr: str) -> "Query":
        self._filters.append(_parse_or(expr))
        return self

    def order(self, column: str, desc: bool = False) -> "Query":
        self._order = (column, desc)
        return self

    def limit(self, n: int) -> "Query":
        self._limit = n
        return self

    def range(self, start: int, end: int) -> "Query":
        self._range = (start, end)
        return self

    # execution
    def _matching(self, rows: list[Row]) -> list[Row]:
        return [r for r in rows if all(f(r) for f in self._filters)]

    def execute(self) -> Result:
        self._db.log.append((self._op, self._table))
        if self._table == "matches_numbered":
            if self._op != "select":  # pragma: no cover - a write to a view
                raise RuntimeError("matches_numbered is a view; writes must target matches")
            rows = self._db.matches_numbered()
        else:
            rows = self._db.tables.setdefault(self._table, [])

        if self._op == "select":
            found = self._matching(rows)
            total = len(found)
            if self._order:
                column, desc = self._order
                found = sorted(found, key=lambda r: (r.get(column) is None, r.get(column)),
                               reverse=desc)
            if self._range:
                start, end = self._range
                found = found[start : end + 1]
            if self._limit is not None:
                found = found[: self._limit]
            data = [] if self._head else [_project(r, self._columns) for r in found]
            return Result(data, count=total if self._count else None)

        if self._op in {"insert", "upsert"}:
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            out: list[Row] = []
            for payload in payloads:
                row = dict(DEFAULTS.get(self._table, {}))
                row.update(payload)
                existing = None
                if self._op == "upsert" and self._on_conflict:
                    keys = [k.strip() for k in self._on_conflict.split(",")]
                    for candidate in rows:
                        if all(str(candidate.get(k)) == str(row.get(k)) for k in keys):
                            existing = candidate
                            break
                if existing is not None:
                    existing.update(payload)
                    out.append(dict(existing))
                    continue
                for column, factory in AUTO.get(self._table, {}).items():
                    row.setdefault(column, factory())
                if self._table == "players" and "member_seq" not in row:
                    row["member_seq"] = 1 + max(
                        (int(r.get("member_seq") or 0) for r in rows), default=0
                    )
                rows.append(row)
                out.append(dict(row))
            return Result(out)

        if self._op == "update":
            touched = self._matching(rows)
            for row in touched:
                row.update(self._payload)
                if "updated_at" in AUTO.get(self._table, {}):
                    row["updated_at"] = _now()
            return Result([dict(r) for r in touched])

        if self._op == "delete":
            touched = self._matching(rows)
            for row in touched:
                rows.remove(row)
            self._db.cascade(self._table, touched)
            return Result([dict(r) for r in touched])

        raise NotImplementedError(self._op)  # pragma: no cover


class _Bucket:
    def __init__(self, db: "MiniSupabase", name: str) -> None:
        self._db, self._name = db, name

    def upload(self, path: str, contents: bytes, options: Row | None = None) -> None:
        self._db.storage_files[f"{self._name}/{path}"] = len(contents)

    def get_public_url(self, path: str) -> str:
        return f"http://storage.test/{self._name}/{path}"


class _Storage:
    def __init__(self, db: "MiniSupabase") -> None:
        self._db = db

    def from_(self, bucket: str) -> _Bucket:
        return _Bucket(self._db, bucket)


class MiniSupabase:
    def __init__(self, tables: dict[str, list[Row]] | None = None) -> None:
        self.tables: dict[str, list[Row]] = tables if tables is not None else {}
        self.storage_files: dict[str, int] = {}
        self.storage = _Storage(self)
        self.log: list[tuple[str, str]] = []

    def table(self, name: str) -> Query:
        return Query(self, name)

    def matches_numbered(self) -> list[Row]:
        ordered = sorted(
            self.tables.get("matches", []), key=lambda r: (r.get("created_at"), str(r.get("id")))
        )
        return [dict(row, match_no=i) for i, row in enumerate(ordered, start=1)]

    def cascade(self, table: str, deleted: list[Row]) -> None:
        """`on delete cascade` from the schema, for the rows the app deletes."""
        if table != "sessions":
            return
        gone = {str(r["id"]) for r in deleted}
        for child in ("checkins", "matches", "billings", "pairing_history", "locked_pairs"):
            kept = [r for r in self.tables.get(child, []) if str(r.get("session_id")) not in gone]
            self.tables[child] = kept
