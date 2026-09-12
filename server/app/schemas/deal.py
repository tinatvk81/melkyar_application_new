from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.deal import DealStatus


class DealCreate(BaseModel):
    property_id: int
    agent_id: int
    deal_amount: int
    commission_percent: Optional[float] = None   # اگر None باشد از درصد مشاور خوانده می‌شود
    contract_date: Optional[date] = None
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    deal_amount: Optional[int] = None
    commission_percent: Optional[float] = None
    contract_date: Optional[date] = None
    notes: Optional[str] = None


class PaymentRead(BaseModel):
    id: int
    amount: int
    paid_date: Optional[date]
    note: Optional[str]
    kind: str = "to_agent"
    has_receipt: bool


class BalanceRead(BaseModel):
    user_id: int
    full_name: str
    username: str
    commission_rates: dict
    earned: int
    paid: int
    remaining: int