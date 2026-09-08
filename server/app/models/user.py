import enum
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    admin = "admin"      # مدیر: دسترسی کامل
    agent = "agent"       # مشاور: فقط فایل‌های خودش


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.agent, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=True)  # برای ارسال یادآوری پیامکی

    # هر بار رمز عبور ریست شود یا کاربر غیرفعال/فعال شود، این عدد +۱ می‌شود
    # تا همه‌ی توکن‌های صادرشده‌ی قبلی فوراً باطل شوند.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

        # درصد پورسانت به تفکیک نوع معامله — مثال: {"sale": 45, "rent": 10, "presale": 30, "mortgage": 8}
    commission_rates: Mapped[dict | None] = mapped_column(JSON, nullable=True)