"""Refuses a request body bigger than any upload the app takes.

The largest file anyone sends is a 5 MB photo (a slip, a receipt, a
product picture); every upload route checks its own limit. But it checks
after reading, and the multipart parser has already taken the whole body
by then — on a server with half a gigabyte of memory, one 500 MB request
is enough to take it down. This stops a body at 8 MB, from the declared
Content-Length when there is one, and by counting as it arrives when there
isn't (a chunked upload). Inside CORSMiddleware, so the 413 keeps its CORS
headers and the page can say the file is too big.
"""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 8 * 1024 * 1024
TOO_BIG = "ไฟล์ใหญ่เกินไป (ไม่เกิน 5MB)"


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope.get("method") in ("GET", "HEAD", "OPTIONS", "DELETE"):
            await self.app(scope, receive, send)
            return
        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None:
            try:
                too_big = int(declared) > self.max_bytes
            except ValueError:
                too_big = False
            if too_big:
                await JSONResponse({"detail": TOO_BIG}, status_code=413)(scope, receive, send)
                return

            await self.app(scope, receive, send)
            return

        # No declared length (a chunked upload): read it here, at most a byte
        # past the limit, and hand it on only if it fits. Counting while the
        # app reads would not do — FastAPI turns any error raised mid-read
        # into a 400, so the 413 would never be seen.
        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                await self.app(scope, receive, send)  # disconnected: let the app see it
                return
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.max_bytes:
                await JSONResponse({"detail": TOO_BIG}, status_code=413)(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
