from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FilterPreset(Base):
    __tablename__ = "filter_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    pending_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")