from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class DiscoveredListing(Base):
    __tablename__ = "discovery_listings"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_discovery_listing_source_ext"),)

    id = Column(Integer, primary_key=True)
    source = Column(String(20), nullable=False)
    external_id = Column(String(64), nullable=False)
    title = Column(String(255))
    raw_address = Column(String(255))
    city = Column(String(50))
    price = Column(BigInteger)
    deposit = Column(BigInteger)
    monthly_rent = Column(BigInteger)
    area_m2 = Column(Integer)
    rooms = Column(Integer)
    deal_type = Column(String(20))
    neighborhood_id = Column(Integer, ForeignKey("discovery_neighborhoods.id"), nullable=True)
    url = Column(String(500))
    attributes = Column(JSONB, nullable=True)
    posted_at = Column(DateTime(timezone=True))
    fetched_at = Column(DateTime(timezone=True))

    converted_property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    converted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)