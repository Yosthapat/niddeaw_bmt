from functools import lru_cache

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import get_settings

# Reads only: a GET that died on the wire can simply be asked again. A
# write that died may already have been applied, so it is never repeated.
SAFE_METHODS = frozenset({"GET", "HEAD"})
READ_RETRIES = 2

# The errors a request gets when its connection is lost under it, before
# any answer came back.
DROPPED = (httpx.ReadError, httpx.RemoteProtocolError, httpx.WriteError)


class RetryDroppedReads(httpx.BaseTransport):
    """Asks a read again when its connection was lost under it.

    Connecting is retried for every request by the inner transport
    (`retries=`), since nothing was sent yet. This adds the other case: the
    connection was up and then dropped mid-request.
    """

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        attempt = 0
        while True:
            try:
                return self.inner.handle_request(request)
            except DROPPED:
                attempt += 1
                if request.method not in SAFE_METHODS or attempt > READ_RETRIES:
                    raise

    def close(self) -> None:
        self.inner.close()


def make_http_client() -> httpx.Client:
    """The one HTTP client every Supabase call goes through.

    supabase-py's own default is a single HTTP/2 connection shared by every
    thread. FastAPI runs each request in its own thread, so a page that asks
    for eight things at once puts eight threads on that one connection, and
    httpx's HTTP/2 is not safe for that: a share of requests fail with
    `ReadError: Resource temporarily unavailable` and the page shows "couldn't
    load". Measured against our Supabase from 8 threads: 17 failures in 960
    requests over HTTP/2, none over HTTP/1.1. So: HTTP/1.1, a pool of
    connections, and the retries above.
    """
    inner = httpx.HTTPTransport(
        http2=False,
        retries=2,
        # Given to the transport, not the client: httpx ignores a client's
        # limits once it has a transport of its own.
        limits=httpx.Limits(max_connections=40, max_keepalive_connections=20, keepalive_expiry=15.0),
    )
    return httpx.Client(
        transport=RetryDroppedReads(inner),
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
    )


@lru_cache
def get_supabase_client() -> Client:
    """Backend-only Supabase client using the service-role key.

    Never import this module from anything that ships to the browser —
    the frontend must only ever talk to this backend's HTTP API.
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=SyncClientOptions(httpx_client=make_http_client()),
    )
