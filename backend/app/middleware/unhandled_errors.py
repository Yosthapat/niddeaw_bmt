"""Turns a crash inside a route into a plain 500 the browser may read.

An exception nobody handled is answered by Starlette's outermost layer,
outside CORSMiddleware, so the 500 goes out without CORS headers. The
browser then hides it from the page completely: fetch() rejects as if the
network were down, and the page tells a member to check their signal when
what happened was a server error (a dropped database connection, most
often). Sitting inside CORSMiddleware, this answers first, so the 500 keeps
its CORS headers and the page can say what really went wrong.
"""

import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class UnhandledErrorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            logger.exception("unhandled error on %s %s", scope.get("method"), scope.get("path"))
            # Half a response already went out: nothing sensible to add.
            if started:
                raise
            await JSONResponse({"detail": "Internal Server Error"}, status_code=500)(scope, receive, send)
