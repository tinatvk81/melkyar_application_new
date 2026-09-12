import enum
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, Date, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FollowUpStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    canceled = "canceled"


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    due_time: Mapped[str | None] = mapped_column(String(5), nullable=True)

    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus), default=FollowUpStatus.pending, nullable=False, index=True
    )
    reminded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )