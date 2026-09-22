"""ستارهٔ شخصی هر کاربر روی فایل‌ها (علاقه‌مندی).
هر کاربر فقط ستاره‌های خودش را می‌بیند؛ ستاره روی فایل‌هایی که دسترسی دیدن دارند
(مشاور: فایل‌های خودش، مدیر: همه)."""
from datetime import datetime, timezone

from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PropertyFavorite(Base):
    __tablename__ = "property_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("user_id", "property_id", name="uq_user_property_favorite"),
    )