"""The endpoint that says what the login throttle makes of a caller.

It exists to settle one question about the deployment — whether two
different people get two different throttle keys — so what matters here is
that it reports the same key the login endpoint would act on, and that it
is not readable by anyone who is not already an admin.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.security import create_access_token
from app.services import login_throttle


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin_id=str(uuid4()), role='admin')}"}


def test_it_is_not_readable_without_logging_in(client: TestClient) -> None:
    assert client.get("/api/admin/auth/whoami").status_code == 401


def test_it_reports_the_hop_our_own_edge_saw(client: TestClient) -> None:
    """The rightmost hop — the leftmost is whatever the client chose to send."""
    body = client.get(
        "/api/admin/auth/whoami",
        headers={**auth(), "X-Forwarded-For": "1.1.1.1, 2.2.2.2, 3.3.3.3"},
    ).json()

    assert body["throttle_key"] == "3.3.3.3"
    assert body["hops"] == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
    assert body["forwarded_for"] == "1.1.1.1, 2.2.2.2, 3.3.3.3"


def test_a_single_hop_is_the_key(client: TestClient) -> None:
    body = client.get(
        "/api/admin/auth/whoami", headers={**auth(), "X-Forwarded-For": "203.0.113.9"}
    ).json()
    assert body["throttle_key"] == "203.0.113.9"


def test_with_no_header_at_all_it_falls_back_to_the_peer(client: TestClient) -> None:
    body = client.get("/api/admin/auth/whoami", headers=auth()).json()
    assert body["forwarded_for"] is None
    assert body["hops"] == []
    assert body["throttle_key"] == body["peer"]


def test_two_callers_behind_different_edges_get_different_keys(client: TestClient) -> None:
    """What the deployment is being measured for, asserted on the code."""
    phone = client.get(
        "/api/admin/auth/whoami", headers={**auth(), "X-Forwarded-For": "198.51.100.7"}
    ).json()
    laptop = client.get(
        "/api/admin/auth/whoami", headers={**auth(), "X-Forwarded-For": "203.0.113.4"}
    ).json()
    assert phone["throttle_key"] != laptop["throttle_key"]


def test_it_reports_the_same_failures_the_login_endpoint_is_counting(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = []
    forwarded = {"X-Forwarded-For": "198.51.100.23"}

    for _ in range(3):
        client.post(
            "/api/admin/auth/login",
            json={"username": "admin", "password": "wrong"},
            headers=forwarded,
        )

    body = client.get("/api/admin/auth/whoami", headers={**auth(), **forwarded}).json()
    assert body["recent_failures"] == 3
    assert body["retry_after_seconds"] == 0  # under the limit, still allowed


def test_it_says_how_long_a_locked_out_caller_must_wait(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = []
    forwarded = {"X-Forwarded-For": "198.51.100.31"}

    for _ in range(login_throttle.MAX_FAILURES):
        client.post(
            "/api/admin/auth/login",
            json={"username": "admin", "password": "wrong"},
            headers=forwarded,
        )

    body = client.get("/api/admin/auth/whoami", headers={**auth(), **forwarded}).json()
    assert body["recent_failures"] == login_throttle.MAX_FAILURES
    assert body["retry_after_seconds"] > 0


def test_one_callers_failures_do_not_show_up_against_another(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The whole point of the per-caller key, asserted end to end."""
    supabase_rows["admins"] = []
    for _ in range(login_throttle.MAX_FAILURES):
        client.post(
            "/api/admin/auth/login",
            json={"username": "admin", "password": "wrong"},
            headers={"X-Forwarded-For": "198.51.100.44"},
        )

    innocent = client.get(
        "/api/admin/auth/whoami", headers={**auth(), "X-Forwarded-For": "203.0.113.77"}
    ).json()
    assert innocent["recent_failures"] == 0
    assert innocent["retry_after_seconds"] == 0
