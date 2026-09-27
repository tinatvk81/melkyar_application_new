from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.discovery.models.listing import DiscoveredListing


def upsert_listing(db: Session, data: dict) -> bool:
    stmt = pg_insert(DiscoveredListing).values(**data)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_discovery_listing_source_ext")
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0