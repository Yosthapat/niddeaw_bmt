"""The HTTP client under every Supabase call: HTTP/1.1, and a read whose
connection dropped is asked again while a write never is."""

from __future__ import annotations

import httpx
import pytest

from app.supabase_client import READ_RETRIES, RetryDroppedReads, make_http_client


class Flaky(httpx.BaseTransport):
    """Drops the connection the first `drops` times, then answers."""

    def __init__(self, drops: int) -> None:
        self.drops = drops
        self.calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls <= self.drops:
            raise httpx.ReadError("Resource temporarily unavailable", request=request)
        return httpx.Response(200, json=[{"ok": True}])


def test_a_read_that_lost_its_connection_is_asked_again() -> None:
    inner = Flaky(drops=READ_RETRIES)
    client = httpx.Client(transport=RetryDroppedReads(inner))
    assert client.get("https://db.example/rest/v1/matches").status_code == 200
    assert inner.calls == READ_RETRIES + 1


def test_a_read_gives_up_after_its_retries() -> None:
    inner = Flaky(drops=READ_RETRIES + 1)
    client = httpx.Client(transport=RetryDroppedReads(inner))
    with pytest.raises(httpx.ReadError):
        client.get("https://db.example/rest/v1/matches")
    assert inner.calls == READ_RETRIES + 1


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_a_write_is_never_repeated(method: str) -> None:
    # It may already have been applied before the connection went.
    inner = Flaky(drops=1)
    client = httpx.Client(transport=RetryDroppedReads(inner))
    with pytest.raises(httpx.ReadError):
        client.request(method, "https://db.example/rest/v1/billings", json={})
    assert inner.calls == 1


def test_supabase_calls_go_over_http_1_1() -> None:
    client = make_http_client()
    transport = client._transport
    assert isinstance(transport, RetryDroppedReads)
    assert isinstance(transport.inner, httpx.HTTPTransport)
    assert transport.inner._pool._http2 is False
    client.close()
