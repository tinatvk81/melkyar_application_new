from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ActivityLogRead(BaseModel):
    id: int
    user_full_name: str
    username: str
    action: str
    entity_type: str
    entity_id: Optional[int]
    detail: Optional[str]
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    items: list[ActivityLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int
