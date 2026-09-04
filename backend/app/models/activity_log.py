from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminActivityLogEntry(BaseModel):
    id: UUID
    admin_id: UUID
    admin_username: str
    action: str
    method: str
    path: str
    detail: dict[str, str] | None = None
    created_at: datetime
