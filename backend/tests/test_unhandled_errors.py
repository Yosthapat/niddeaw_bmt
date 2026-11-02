"""A crash inside a route still answers with CORS headers.

Without them the browser hides the 500 from the page, which can then only
say "no connection" — the wrong advice for a server error, and what members
saw on the finance charts.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app

ORIGIN = "http://localhost:5173"  # in CORS_ORIGINS for the tests, see conftest

router = APIRouter()


@router.get("/api/__test__/boom")
def boom() -> None:
    raise RuntimeError("database went away")


app.include_router(router)


def test_a_crash_is_a_500_the_browser_is_allowed_to_read() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/__test__/boom", headers={"Origin": ORIGIN})
    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == ORIGIN
    assert response.json() == {"detail": "Internal Server Error"}
