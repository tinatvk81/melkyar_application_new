from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ClientRequestCreate(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    deal_type: str
    city: Optional[str] = None
    district: Optional[str] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    min_rooms: Optional[int] = None
    max_price: Optional[int] = None
    notes: Optional[str] = None


class ClientRequestUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    deal_type: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    min_rooms: Optional[int] = None
    max_price: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ClientRequestRead(BaseModel):
    id: int
    owner_agent_id: int
    customer_name: str
    customer_phone: Optional[str]
    deal_type: str
    city: Optional[str]
    district: Optional[str]
    min_area: Optional[float]
    max_area: Optional[float]
    min_rooms: Optional[int]
    max_price: Optional[int]
    notes: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True