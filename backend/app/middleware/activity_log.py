from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.deps import get_current_admin
from app.services.activity_log_service import LOGGED_METHODS, describe_action
from app.supabase_client import get_supabase_client

_SKIP_PATHS = {"/api/admin/auth/login"}


class AdminActivityLogMiddleware(BaseHTTPMiddleware):
    """Logs every successful admin write (POST/PATCH/PUT/DELETE under
    /api/admin/*) to admin_activity_log — generically, so new admin
    endpoints are covered without remembering to add a log call to each
    one. Best-effort: a logging failure never breaks the underlying
    request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path
        if (
            request.method in LOGGED_METHODS
            and path.startswith("/api/admin/")
            and path not in _SKIP_PATHS
            and 200 <= response.status_code < 300
        ):
            self._log(request, path)

        return response

    def _log(self, request: Request, path: str) -> None:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return
        try:
            admin = get_current_admin(auth_header)
        except Exception:
            return

        detail: dict[str, Any] = dict(request.path_params)
        try:
            get_supabase_client().table("admin_activity_log").insert(
                {
                    "admin_id": str(admin.admin_id),
                    "action": describe_action(request.method, path),
                    "method": request.method,
                    "path": path,
                    "detail": detail or None,
                }
            ).execute()
        except Exception:
            pass
