import enum
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, Float, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DealStatus(str, enum.Enum):
    pending = "pending"        # قولنامه ثبت شده، هنوز قطعی نشده
    finalized = "finalized"    # قطعی شده — پورسانت رسمی می‌شود
    canceled = "canceled"      # لغو شده


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    deal_amount: Mapped[int] = mapped_column(Integer, nullable=False)          # مبلغ کل معامله (تومان)
    commission_percent: Mapped[float] = mapped_column(Float, nullable=False)   # درصد پورسانت این معامله
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)    # پورسانت (تومان)

    status: Mapped[DealStatus] = mapped_column(
        Enum(DealStatus), default=DealStatus.pending, nullable=False, index=True
    )

    contract_date: Mapped[date] = mapped_column(Date, nullable=True)
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CommissionPayment(Base):
    __tablename__ = "commission_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_date: Mapped[date] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    receipt_path: Mapped[str] = mapped_column(String(255), nullable=True)   # عکس رسید
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )