from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PropertyImage(Base):
    """
    متادیتای عکس‌های هر فایل ملکی. خودِ فایل عکس روی دیسک سرور در پوشه‌ی
    media/properties/{property_id}/{stored_filename} ذخیره می‌شود — نه در دیتابیس —
    چون ذخیره‌ی باینری حجیم داخل دیتابیس، بک‌آپ‌گیری و کارایی را در بلندمدت
    (با ۱۰٬۰۰۰+ فایل و عکس‌های همراهشان) سنگین می‌کند.
    نکته‌ی مهم: پوشه‌ی media باید مثل دیتابیس در استراتژی بک‌آپ (backup.py) لحاظ شود؛
    این از قبل در آن اسکریپت در نظر گرفته شده است.
    """
    __tablename__ = "property_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    stored_filename: Mapped[str] = mapped_column(String(128), nullable=False)  # نام تصادفی روی دیسک (uuid)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=True)  # نام اصلی فایل کاربر (فقط نمایشی)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
