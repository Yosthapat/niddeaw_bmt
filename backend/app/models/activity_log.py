from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AdminActivityLogEntry(BaseModel):
    id: UUID
    admin_id: UUID
    admin_username: str
    action: str
    method: str
    path: str
    # Mostly the path's ids as text; a deleted shop order also keeps what
    # it was (its number, its lines, its total), so values are any JSON.
    detail: dict[str, Any] | None = None
    created_at: datetime
