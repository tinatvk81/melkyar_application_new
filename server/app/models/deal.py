import enum
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, BigInteger, Numeric, Float, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DealStatus(str, enum.Enum):
    pending = "pending"
    finalized = "finalized"
    canceled = "canceled"


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # --- معاملهٔ مشارکتی: مشاور دوم + تقسیم درصد (مثلاً کل ۴۰٪ → ۲۵+۱۵) ---
    agent2_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    commission_percent_agent2: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # NUMERIC بدون دقت = بدون سقف عملی (تا ۱۳۱٬۰۷۲ رقم) — برخلاف BigInteger که تا ۹.۲×۱۰¹۸
    deal_amount: Mapped[int] = mapped_column(Numeric, nullable=False)
    commission_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    commission_amount: Mapped[int] = mapped_column(Numeric, nullable=False)

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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CommissionPayment(Base):
    __tablename__ = "commission_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Numeric, nullable=False)
    paid_date: Mapped[date] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    receipt_path: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="to_agent", server_default="to_agent")