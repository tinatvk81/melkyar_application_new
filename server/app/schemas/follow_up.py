from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class FollowUpCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    property_id: Optional[int] = None
    deal_id: Optional[int] = None


class FollowUpUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None


class FollowUpRead(BaseModel):
    id: int
    user_id: int
    property_id: Optional[int]
    deal_id: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[date]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationRead(BaseModel):
    id: int
    title: str
    body: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True