"""Drops the cached tournament (services/tournament_cache.py) around every
write to it — before, so the route's own reply reads fresh rows, and after,
so a read that raced the write can't leave the old ones behind."""

from starlette.types import ASGIApp, Receive, Scope, Send

from app.services import tournament_cache

WRITES_TO = ("/api/admin/tournament", "/api/line/tournament")
READS = frozenset({"GET", "HEAD", "OPTIONS"})


class TournamentCacheMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        writes = (
            scope["type"] == "http"
            and scope.get("method") not in READS
            and str(scope.get("path", "")).startswith(WRITES_TO)
        )
        if not writes:
            await self.app(scope, receive, send)
            return
        tournament_cache.invalidate()
        try:
            await self.app(scope, receive, send)
        finally:
            tournament_cache.invalidate()
