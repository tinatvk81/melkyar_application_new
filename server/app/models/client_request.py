import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequestStatus(str, enum.Enum):
    open = "open"      # در جست‌وجوی فایل
    closed = "closed"  # بسته شده (معامله شد یا منصرف شد)


class ClientRequest(Base):
    __tablename__ = "client_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=True)
    deal_type: Mapped[str] = mapped_column(String(16), nullable=False)  # sale/rent/mortgage/presale

    city: Mapped[str] = mapped_column(String(64), nullable=True)
    district: Mapped[str] = mapped_column(String(64), nullable=True)
    min_area: Mapped[float] = mapped_column(Float, nullable=True)
    max_area: Mapped[float] = mapped_column(Float, nullable=True)
    min_rooms: Mapped[int] = mapped_column(Integer, nullable=True)
    max_price: Mapped[int] = mapped_column(Integer, nullable=True)  # سقف بودجه (تومان)

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.open, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )