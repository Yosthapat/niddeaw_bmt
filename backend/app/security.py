from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(admin_id: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": admin_id, "role": role, "exp": expire}
    return str(jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM))


# What a token is for. An admin's says "admin"; a member signed in with
# LINE gets "line", which no admin route accepts (deps.get_current_admin)
# and which carries their LINE user id, never an admin id.
ADMIN_ROLE = "admin"
LINE_ROLE = "line"


def create_line_token(line_user_id: str, line_name: str, line_picture: str | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.line_token_minutes)
    payload = {"sub": line_user_id, "role": LINE_ROLE, "name": line_name, "pic": line_picture, "exp": expire}
    return str(jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM))


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    return payload
