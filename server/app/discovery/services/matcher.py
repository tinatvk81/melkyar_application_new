from sqlalchemy.orm import Session
from app.discovery.models.neighborhood import DiscoveryNeighborhood


def match_neighborhood(text: str, db: Session) -> int | None:
    text_normalized = (text or "").strip()
    neighborhoods = db.query(DiscoveryNeighborhood).all()
    for n in neighborhoods:
        candidates = [n.name] + (n.aliases.split(",") if n.aliases else [])
        for c in candidates:
            if c.strip() and c.strip() in text_normalized:
                return n.id
    return None