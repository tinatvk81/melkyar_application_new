from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.db.base import Base


class DiscoveryNotificationLog(Base):
    __tablename__ = "discovery_notification_logs"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, nullable=True)
    channel = Column(String(20))
    body = Column(Text)
    created_at = Column(DateTime(timezone=True))