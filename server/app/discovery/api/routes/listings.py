from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.activity_log_service import log_activity
from app.discovery.models.listing import DiscoveredListing
from app.discovery.services.convert_to_property import build_property_from_listing

router = APIRouter(prefix="/discovery", tags=["ملک‌یاب"])


class DiscoveryListingRead(BaseModel):
    id: int
    source: str
    external_id: str
    title: Optional[str] = None
    raw_address: Optional[str] = None
    city: Optional[str] = None
    price: Optional[int] = None
    deposit: Optional[int] = None
    monthly_rent: Optional[int] = None
    area_m2: Optional[int] = None
    rooms: Optional[int] = None
    deal_type: Optional[str] = None
    neighborhood_id: Optional[int] = None
    url: Optional[str] = None
    attributes: Optional[dict] = None
    posted_at: Optional[datetime] = None
    converted_property_id: Optional[int] = None

    class Config:
        from_attributes = True


class DismissIn(BaseModel):
    property_id: Optional[int] = None


@router.get("/listings", response_model=list[DiscoveryListingRead])
def list_discovered(only_new: bool = True, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = db.query(DiscoveredListing)
    if only_new:
        q = q.filter(DiscoveredListing.converted_property_id.is_(None),
                     DiscoveredListing.dismissed_at.is_(None))
    return q.order_by(DiscoveredListing.posted_at.desc()).limit(200).all()


@router.get("/listings/{listing_id}", response_model=DiscoveryListingRead)
def get_listing(listing_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    return listing


@router.post("/listings/{listing_id}/convert-to-file")
def convert_to_file(listing_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    if listing.converted_property_id is not None:
        raise HTTPException(400, "این آگهی قبلاً به فایل تبدیل شده")

    new_property = build_property_from_listing(listing, db, owner_agent_id=user.id)
    db.add(new_property)
    db.flush()

    listing.converted_property_id = new_property.id
    listing.converted_by_user_id = user.id
    listing.converted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_property)

    log_activity(db, user.id, "create", "property", new_property.id,
                 detail=f"وارد شده از ملک‌یاب — {new_property.city} — {new_property.district or ''}")
    return {"status": "ok", "property_id": new_property.id}


@router.post("/listings/{listing_id}/dismiss")
def dismiss_listing(listing_id: int, data: DismissIn | None = None,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """نادیده‌گرفتن؛ و اگر property_id بیاید یعنی همین الان از طریق فرم به فایل تبدیل شد —
    لینک آگهی↔فایل حفظ می‌شود و از «یافته‌های جدید» حذف می‌شود."""
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    listing.dismissed_at = datetime.now(timezone.utc)
    listing.converted_by_user_id = user.id
    if data and data.property_id:
        listing.converted_property_id = data.property_id
    listing.converted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "dismissed"}