from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.property import Property, DealType
from app.discovery.models.listing import DiscoveredListing
from app.discovery.models.neighborhood import DiscoveryNeighborhood

DEAL_TYPE_MAP = {"sale": DealType.sale, "rent": DealType.rent, "mortgage": DealType.mortgage}


def build_property_from_listing(listing: DiscoveredListing, db: Session, owner_agent_id: int) -> Property:
    deal_type = DEAL_TYPE_MAP.get(listing.deal_type, DealType.sale)

    district = None
    if listing.neighborhood_id:
        n = db.get(DiscoveryNeighborhood, listing.neighborhood_id)
        district = n.name if n else None

    details = {}
    if deal_type == DealType.sale and listing.price:
        details["price"] = listing.price
    elif deal_type == DealType.rent:
        if listing.deposit and listing.monthly_rent:
            details["deposit"] = listing.deposit
            details["monthly_rent"] = listing.monthly_rent
        elif listing.deposit:
            deal_type = DealType.mortgage
            details["deposit_full"] = listing.deposit

    attrs = listing.attributes or {}
    note_lines = [f"وارد شده از ملک‌یاب — منبع: {listing.source}", listing.title or "", listing.url or ""]
    desc = (attrs.get("description") or "").strip()
    if desc:
        note_lines.append("— توضیحات آگهی —")
        note_lines.append(desc[:800])

    if listing.posted_at:
        note_lines.append(f"تاریخ انتشار آگهی: {listing.posted_at.date().isoformat()}")
        
    return Property(
        deal_type=deal_type,
        city=listing.city or "مشهد",
        district=district,
        address=listing.raw_address,
        area_m2=listing.area_m2,
        rooms=listing.rooms,
        build_year=attrs.get("build_year"),
        amenities=attrs.get("amenities") or None,
        details=details,
        notes="\n".join(line for line in note_lines if line),
        owner_name=attrs.get("advertiser"),   # نام آگهی‌دهنده — فقط وقتی دیوار نمایشش داده
        owner_agent_id=owner_agent_id,
    )