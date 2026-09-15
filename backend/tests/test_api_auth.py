"""The auth surface of the HTTP API.

Everything else under tests/ exercises a service function directly. Nothing
went through the app itself, which left the one bug class you cannot catch
that way with no coverage at all: an admin endpoint that forgets `AdminDep`
and is simply open. The sweep below reads the routes off the app, so an
endpoint added without a guard fails here on arrival rather than whenever
somebody next thinks to look.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.security import ALGORITHM, decode_access_token, hash_password
from app.services import login_throttle

LOGIN = "/api/admin/auth/login"
# The only admin route that must be reachable without a token — you cannot
# present one before you have logged in.
OPEN_ADMIN_ROUTES = {LOGIN}


def admin_routes() -> list[tuple[str, str]]:
    """Every (method, path) the app serves under /api/admin/, read from the
    app itself rather than a list someone has to remember to update.

    Taken from the OpenAPI schema rather than by walking `app.routes`: this
    FastAPI version keeps included routers nested rather than flattened, so
    a naive scan of `app.routes` finds nothing at all — which would have
    made the sweep below pass while checking zero endpoints."""
    found: list[tuple[str, str]] = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/admin/") or path in OPEN_ADMIN_ROUTES:
            continue
        for method in operations:
            if method.lower() in {"head", "options"}:
                continue
            found.append((method.upper(), path))
    return sorted(found)


def call(client: TestClient, method: str, path: str, **kwargs: Any) -> Any:
    # Path params are never reached: the guard runs first, so any syntactically
    # valid value does.
    concrete = path.replace("{session_id}", "00000000-0000-0000-0000-000000000000")
    for name in ("player_id", "billing_id", "match_id", "checkin_id", "lock_id", "expense_id",
                 "income_id", "admin_id", "id"):
        concrete = concrete.replace("{" + name + "}", "00000000-0000-0000-0000-000000000000")
    return client.request(method, concrete, **kwargs)


def test_there_are_admin_routes_to_check() -> None:
    """Guards the sweep itself: if the route scan ever silently returns
    nothing, the tests below would all pass while checking nothing."""
    assert len(admin_routes()) > 20


@pytest.mark.parametrize("method,path", admin_routes())
def test_admin_route_rejects_a_caller_with_no_token(
    client: TestClient, method: str, path: str
) -> None:
    assert call(client, method, path).status_code == 401


@pytest.mark.parametrize("method,path", admin_routes())
def test_admin_route_rejects_a_token_it_cannot_verify(
    client: TestClient, method: str, path: str
) -> None:
    forged = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "role": "admin",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "not-the-servers-secret",
        algorithm=ALGORITHM,
    )
    response = call(client, method, path, headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_admin_route_rejects_an_expired_token(client: TestClient) -> None:
    from app.config import get_settings

    expired = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "role": "admin",
         "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        get_settings().jwt_secret,
        algorithm=ALGORITHM,
    )
    response = client.get("/api/admin/sessions", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "header",
    ["", "Bearer", "Bearer ", "Basic abc", "token abc", "Bearer not.a.jwt"],
)
def test_malformed_authorization_headers_are_rejected(client: TestClient, header: str) -> None:
    response = client.get("/api/admin/sessions", headers={"Authorization": header})
    assert response.status_code == 401


def test_public_routes_need_no_token(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The mirror of the sweep: the public site must keep working for
    everyone, so these must never start demanding auth."""
    for path in ("/health", "/api/players", "/api/ranking", "/api/matches", "/api/seasons"):
        assert client.get(path).status_code != 401


# --- login itself ---------------------------------------------------------

ADMIN_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "username": "boss",
    "password_hash": hash_password("correct-horse"),
    "role": "admin",
}


def test_login_returns_a_token_the_server_can_verify(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    response = client.post(LOGIN, json={"username": "boss", "password": "correct-horse"})
    assert response.status_code == 200
    payload = decode_access_token(response.json()["access_token"])
    assert payload["sub"] == ADMIN_ROW["id"]
    assert payload["role"] == "admin"


def test_login_rejects_a_wrong_password(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    assert client.post(LOGIN, json={"username": "boss", "password": "nope"}).status_code == 401


def test_login_rejects_an_unknown_username(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = []
    assert client.post(LOGIN, json={"username": "ghost", "password": "nope"}).status_code == 401


def test_login_never_echoes_the_password_hash(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    response = client.post(LOGIN, json={"username": "boss", "password": "correct-horse"})
    assert ADMIN_ROW["password_hash"] not in response.text


# --- the throttle, through the endpoint -----------------------------------


def test_the_sixth_wrong_password_is_refused_outright(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    bad = {"username": "boss", "password": "nope"}
    for _ in range(login_throttle.MAX_FAILURES):
        assert client.post(LOGIN, json=bad).status_code == 401

    blocked = client.post(LOGIN, json=bad)
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["Retry-After"]) <= login_throttle.WINDOW_SECONDS + 1


def test_the_right_password_is_refused_too_once_throttled(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Otherwise the throttle is an oracle: a caller could tell a correct
    guess from a wrong one by which of them still gets through."""
    supabase_rows["admins"] = [ADMIN_ROW]
    for _ in range(login_throttle.MAX_FAILURES):
        client.post(LOGIN, json={"username": "boss", "password": "nope"})

    response = client.post(LOGIN, json={"username": "boss", "password": "correct-horse"})
    assert response.status_code == 429


def test_getting_in_forgives_the_typos_before_it(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    for _ in range(login_throttle.MAX_FAILURES - 1):
        client.post(LOGIN, json={"username": "boss", "password": "nope"})

    assert client.post(LOGIN, json={"username": "boss", "password": "correct-horse"}).status_code == 200
    # Budget back to full: four more wrong tries must not trip it.
    for _ in range(login_throttle.MAX_FAILURES - 1):
        assert client.post(LOGIN, json={"username": "boss", "password": "nope"}).status_code == 401


def test_one_caller_being_throttled_does_not_lock_out_another(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    supabase_rows["admins"] = [ADMIN_ROW]
    attacker = {"X-Forwarded-For": "203.0.113.9"}
    for _ in range(login_throttle.MAX_FAILURES):
        client.post(LOGIN, json={"username": "boss", "password": "nope"}, headers=attacker)
    assert client.post(LOGIN, json={"username": "boss", "password": "nope"},
                       headers=attacker).status_code == 429

    admin = {"X-Forwarded-For": "198.51.100.4"}
    assert client.post(LOGIN, json={"username": "boss", "password": "correct-horse"},
                       headers=admin).status_code == 200


def test_a_spoofed_forwarded_for_does_not_buy_a_fresh_budget(
    client: TestClient, supabase_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """The attack the rightmost-hop rule exists to stop: the caller writes
    their own X-Forwarded-For and the proxy appends the address it really
    saw, so only the last entry is theirs to fake."""
    supabase_rows["admins"] = [ADMIN_ROW]
    bad = {"username": "boss", "password": "nope"}
    for i in range(login_throttle.MAX_FAILURES):
        headers = {"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.9"}
        assert client.post(LOGIN, json=bad, headers=headers).status_code == 401

    # A brand-new left-hand value, same real peer on the right.
    response = client.post(LOGIN, json=bad, headers={"X-Forwarded-For": "10.0.0.99, 203.0.113.9"})
    assert response.status_code == 429
