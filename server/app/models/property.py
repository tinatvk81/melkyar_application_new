"""
تصمیم طراحی (برای شروع ساده و سریع‌تر):
به‌جای ۴ جدول کاملاً جدا برای فروش/پیش‌خرید/اجاره/رهن‌کامل، یک جدول Property
با فیلدهای مشترک + یک ستون JSONB به نام `details` برای فیلدهای اختصاصی هر نوع
معامله استفاده شده. Postgres در JSONB هم فیلتر و هم ایندکس‌گذاری را پشتیبانی
می‌کند، پس چیزی از دست نمی‌رود ولی کد اولیه بسیار ساده‌تر می‌ماند.
اگر بعداً حجم/پیچیدگی بالا رفت، می‌شود این را به جدول‌های جدا تبدیل کرد (Alembic).
"""
import enum
from datetime import datetime, date, timezone

from sqlalchemy import String, Integer, Float, Date, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DealType(str, enum.Enum):
    sale = "sale"              # فروش
    presale = "presale"         # پیش‌خرید
    rent = "rent"               # اجاره
    mortgage = "mortgage"        # رهن کامل


class PropertyStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"   # به‌جای حذف قطعی، فقط غیرفعال می‌شود


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- قفل هم‌زمان (Optimistic Locking) ---
    # با هر ویرایش موفق +۱ می‌شود. کلاینت باید همان نسخه‌ای که خوانده را در
    # درخواست ویرایش بفرستد؛ اگر با نسخه‌ی فعلی دیتابیس فرق داشت (یعنی شخص
    # دیگری بین‌این‌حین فایل را عوض کرده)، سرور با خطای ۴۰۹ رد می‌کند به‌جای
    # این‌که بی‌صدا تغییرات آن شخص دیگر را رونویسی کند.
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # --- مالکیت فایل (برای فیلتر دسترسی مشاور) ---
    owner_agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # --- فیلدهای مشترک ---
    deal_type: Mapped[DealType] = mapped_column(Enum(DealType), nullable=False, index=True)
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus), default=PropertyStatus.active, nullable=False, index=True
    )
    city: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(64), nullable=True)  # منطقه/محله
    address: Mapped[str] = mapped_column(String(255), nullable=True)
    area_m2: Mapped[float] = mapped_column(Float, nullable=True)  # متراژ
    rooms: Mapped[int] = mapped_column(Integer, nullable=True)   # تعداد اتاق
    has_elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    has_parking: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_name: Mapped[str] = mapped_column(String(128), nullable=True)   # مالک ملک
    owner_phone: Mapped[str] = mapped_column(String(32), nullable=True)

    # فقط برای اجاره/رهن: تاریخ پایان قرارداد (برای ماژول یادآوری)
    contract_end_date: Mapped[date] = mapped_column(Date, nullable=True, index=True)

    # فیلدهای اختصاصی هر نوع معامله، مثلا:
    # sale: {"price": 5200000000}
    # presale: {"total_price": ..., "delivery_date": "1404-06-01", "installments": [...]}
    # rent: {"monthly_rent": ..., "deposit": ...}
    # mortgage: {"deposit_full": ...}
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    notes: Mapped[str] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
