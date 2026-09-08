from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.property import DealType, PropertyStatus


class PropertyCreate(BaseModel):
    deal_type: DealType
    city: str
    district: Optional[str] = None
    address: Optional[str] = None
    area_m2: Optional[float] = None
    rooms: Optional[int] = None
    has_elevator: bool = False
    has_parking: bool = False
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    contract_end_date: Optional[date] = None
    details: dict = {}
    notes: Optional[str] = None
    amenities: list[str] | None = None


class PropertyUpdate(PropertyCreate):
    status: Optional[PropertyStatus] = None
    # قفل هم‌زمان: کلاینت باید نسخه‌ای که خوانده را برگرداند تا سرور بتواند
    # تشخیص دهد آیا از آخرین باری که این فایل را دید، شخص دیگری تغییرش داده یا نه.
    version: int
    amenities: list[str] | None = None


class PropertyRead(BaseModel):
    id: int
    version: int
    owner_agent_id: int
    deal_type: DealType
    status: PropertyStatus
    city: str
    district: Optional[str]
    address: Optional[str]
    area_m2: Optional[float]
    rooms: Optional[int]
    has_elevator: bool
    has_parking: bool
    owner_name: Optional[str]
    owner_phone: Optional[str]
    contract_end_date: Optional[date]
    details: dict
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    amenities: list[str] | None = None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    """
    پاسخ صفحه‌بندی‌شده‌ی فهرست فایل‌ها. برخلاف نسخه‌ی قبلی که فقط یک لیست خام
    برمی‌گرداند (و در مقیاس بزرگ فایل‌های بعد از ۵۰۰ اُم را بی‌صدا پنهان می‌کرد)،
    این نسخه تعداد کل و اطلاعات صفحه‌بندی را هم می‌فرستد تا کلاینت بتواند
    «صفحه X از Y — تعداد کل: N» را درست نمایش دهد.
    """
    items: list[PropertyRead]
    total: int
    page: int
    page_size: int
    total_pages: int
