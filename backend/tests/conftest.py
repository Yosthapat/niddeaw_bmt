"""Shared fixtures for the API-level tests.

The env vars are set before `app.main` is imported, not in a fixture:
`main.py` calls `get_settings()` at import time and both `get_settings` and
`get_supabase_client` are `lru_cache`d, so a later monkeypatch.setenv would
be read after the value it wanted to change was already frozen.
"""

import os
from collections.abc import Iterator
from typing import Any

os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-real"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.deps import get_supabase  # noqa: E402
from app.main import app  # noqa: E402
from app.services import login_throttle  # noqa: E402


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.data = rows
        self.count = len(rows)


class FakeQuery:
    """Just enough of the supabase-py builder for these tests.

    Any builder call (`select`, `eq`, `order`, `range`, `in_`, …) is a no-op
    returning self, via __getattr__ rather than a hand-written list — the
    routers reach for a wide spread of them and enumerating those here would
    be a second copy of postgrest's API to keep in step. `execute()` hands
    back whatever rows the test loaded. Filtering and ordering are the
    service layer's job and are tested there, against the real logic.
    """

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def __getattr__(self, name: str) -> Any:
        def builder(*args: Any, **kwargs: Any) -> "FakeQuery":
            return self

        return builder

    def execute(self) -> FakeResult:
        return FakeResult(self._rows)


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.tables = tables or {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.tables.get(name, []))


@pytest.fixture(autouse=True)
def _clean_throttle() -> Iterator[None]:
    """The throttle keeps module-level state, so without this the order the
    tests happen to run in would decide their outcomes."""
    login_throttle.reset_all()
    yield
    login_throttle.reset_all()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def supabase_rows() -> Iterator[dict[str, list[dict[str, Any]]]]:
    """Load rows per table, then call the API through `client`."""
    tables: dict[str, list[dict[str, Any]]] = {}
    app.dependency_overrides[get_supabase] = lambda: FakeSupabase(tables)
    yield tables
    app.dependency_overrides.pop(get_supabase, None)
