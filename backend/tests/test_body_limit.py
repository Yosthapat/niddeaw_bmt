"""An upload bigger than anything the app takes is refused before it is
read (app/middleware/body_limit.py)."""

from collections.abc import Iterator

from fastapi.testclient import TestClient

from app.middleware.body_limit import MAX_BODY_BYTES


def test_a_declared_oversized_body_is_refused_up_front(client: TestClient) -> None:
    big = b"0" * (MAX_BODY_BYTES + 1)
    answer = client.post(
        "/api/admin/players/x/avatar",
        content=big,
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert answer.status_code == 413
    assert "5MB" in answer.json()["detail"]


def test_an_oversized_chunked_body_is_cut_off(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(MAX_BODY_BYTES // (1024 * 1024) + 2):
            yield b"0" * (1024 * 1024)

    # A JSON route reads the whole body, so this one is cut off by counting.
    answer = client.post(
        "/api/admin/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert answer.status_code == 413


def test_ordinary_requests_pass(client: TestClient) -> None:
    assert client.get("/api/line/config").status_code == 200
    assert client.post("/api/admin/auth/login", json={"username": "x"}).status_code in (401, 422)
