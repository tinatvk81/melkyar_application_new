from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class DiscoverySubscription(Base):
    __tablename__ = "discovery_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    allowed_districts = Column(JSONB, nullable=True)   # خالی/None = همهٔ محله‌ها
    blocked_districts = Column(JSONB, nullable=True)   # هرگز نشان نده
    deal_types = Column(JSONB, nullable=True)          # خالی/None = همه
    show_unknown = Column(Boolean, nullable=False, default=True)