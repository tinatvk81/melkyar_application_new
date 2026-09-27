from sqlalchemy import Column, Integer, String
from app.db.base import Base


class DiscoveryNeighborhood(Base):
    __tablename__ = "discovery_neighborhoods"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    aliases = Column(String(255), nullable=True)