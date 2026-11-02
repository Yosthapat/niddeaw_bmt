"""What a request hears when the database refuses a write.

The routers check what they can before writing — a nickname nobody else
has, a session still open, a size the product sells — but Postgres has the
last word: a unique key two admins raced for, a row another one deleted a
moment ago, a check constraint a value slipped past. supabase-py raises
those as postgrest's APIError, and nothing caught it, so each one ended as
a bare 500 and the page could only say "something went wrong".

These are the caller's mistakes, not the server's, so they are answered as
4xx with a reason the admin can act on. Anything else (a dropped
connection, a permissions error) stays a 500 for UnhandledErrorsMiddleware.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

# Postgres SQLSTATE -> (HTTP status, what to tell the admin).
_REFUSALS: dict[str, tuple[int, str]] = {
    "23505": (409, "ข้อมูลนี้มีอยู่แล้ว — รีเฟรชหน้าแล้วลองใหม่"),
    "23503": (409, "ข้อมูลที่อ้างถึงไม่มีอยู่แล้ว หรือยังถูกใช้อยู่ที่อื่น — รีเฟรชหน้าแล้วลองใหม่"),
    "23502": (400, "ข้อมูลไม่ครบ — มีช่องที่ต้องกรอก"),
    "23514": (400, "ข้อมูลไม่ถูกต้อง — ตรวจค่าที่กรอกอีกครั้ง"),
    "22001": (400, "ข้อความยาวเกินไป"),
    "22003": (400, "ตัวเลขมากเกินไป"),
    "22P02": (400, "รูปแบบข้อมูลไม่ถูกต้อง"),
    "22007": (400, "วันที่ไม่ถูกต้อง"),
    "22008": (400, "วันที่ไม่ถูกต้อง"),
}


def refusal(error: APIError) -> tuple[int, str] | None:
    return _REFUSALS.get(str(error.code or ""))


async def _on_api_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, APIError)
    found = refusal(exc)
    if found is None:
        raise exc
    code, detail = found
    logger.warning("database refused %s %s: %s %s", request.method, request.url.path, exc.code, exc.message)
    return JSONResponse({"detail": detail}, status_code=code)


def register(app: FastAPI) -> None:
    app.add_exception_handler(APIError, _on_api_error)
