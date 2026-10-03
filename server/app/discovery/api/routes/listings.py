from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.activity_log_service import log_activity
from app.discovery.models.listing import DiscoveredListing
from app.discovery.models.neighborhood import DiscoveryNeighborhood
from app.discovery.models.subscription import DiscoverySubscription
from app.discovery.services.convert_to_property import build_property_from_listing
from app.discovery.services.details import fetch_details, enrich_from_payload

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


class BulkAddIn(BaseModel):
    listing_ids: list[int]


class AssignIn(BaseModel):
    neighborhood_id: int


class SubscriptionIn(BaseModel):
    allowed_districts: list[str] = []
    blocked_districts: list[str] = []
    deal_types: list[str] = []
    show_unknown: bool = True


@router.get("/neighborhoods")
def list_neighborhoods(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": n.id, "name": n.name}
            for n in db.query(DiscoveryNeighborhood).order_by(DiscoveryNeighborhood.name).all()]


def _get_subscription(db: Session, user: User) -> Optional[DiscoverySubscription]:
    return db.query(DiscoverySubscription).filter_by(user_id=user.id).first()


def _apply_subscription(q, db: Session, sub: Optional[DiscoverySubscription]):
    if not sub:
        return q
    names = {n.name: n.id for n in db.query(DiscoveryNeighborhood).all()}
    blocked = [names[x] for x in (sub.blocked_districts or []) if x in names]
    allowed = [names[x] for x in (sub.allowed_districts or []) if x in names]
    if sub.deal_types:
        q = q.filter(DiscoveredListing.deal_type.in_(sub.deal_types))
    if blocked:
        q = q.filter(or_(DiscoveredListing.neighborhood_id.is_(None),
                         ~DiscoveredListing.neighborhood_id.in_(blocked)))
    if allowed:
        cond = DiscoveredListing.neighborhood_id.in_(allowed)
        if sub.show_unknown:
            cond = or_(cond, DiscoveredListing.neighborhood_id.is_(None))
        q = q.filter(cond)
    elif not sub.show_unknown:
        q = q.filter(DiscoveredListing.neighborhood_id.isnot(None))
    return q


@router.get("/listings", response_model=list[DiscoveryListingRead])
def list_discovered(only_new: bool = True, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = db.query(DiscoveredListing)
    if only_new:
        q = q.filter(DiscoveredListing.converted_property_id.is_(None),
                     DiscoveredListing.dismissed_at.is_(None))
    q = _apply_subscription(q, db, _get_subscription(db, user))
    return q.order_by(DiscoveredListing.posted_at.desc()).limit(200).all()


@router.get("/listings/{listing_id}", response_model=DiscoveryListingRead)
def get_listing(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    return listing


@router.post("/listings/{listing_id}/refresh-details", response_model=DiscoveryListingRead)
def refresh_details(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """دریافت جزئیات کامل (بدون شماره) در لحظهٔ کلیک مشاور — هر دو منبع."""
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    _ensure_enriched(db, listing)
    return listing

def _ensure_enriched(db: Session, listing: DiscoveredListing):
    """تضمین: هر آگهی موقع تبدیل به فایل، جزئیات کامل (توضیح/امکانات/سال/طبقه) دارد."""
    if (listing.attributes or {}).get("has_details"):
        return
    if listing.source == "sheypoor":
        from app.discovery.services.details import fetch_sheypoor_details, enrich_from_sheypoor_payload
        payload = fetch_sheypoor_details(listing.external_id)
        if payload:
            enrich_from_sheypoor_payload(listing, payload)
    else:
        payload = fetch_details(listing.external_id)
        if payload:
            enrich_from_payload(listing, payload)
    db.commit()
    db.refresh(listing)


@router.post("/listings/bulk-add")
def bulk_add(data: BulkAddIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.schemas.property import PropertyRead
    created, failed = [], []
    for lid in data.listing_ids[:50]:
        listing = db.get(DiscoveredListing, lid)
        if not listing or listing.converted_property_id is not None:
            failed.append({"id": lid, "reason": "ناموجود یا قبلاً اضافه شده"})
            continue
        _ensure_enriched(db, listing)             
        p = build_property_from_listing(listing, db, owner_agent_id=user.id)
        db.add(p)
        db.flush()
        listing.converted_property_id = p.id
        listing.converted_by_user_id = user.id
        listing.converted_at = datetime.now(timezone.utc)
        db.flush()
        created.append({"listing_id": lid, "property_id": p.id,
                        "property": PropertyRead.model_validate(p).model_dump(mode="json")})
    db.commit()
    for c in created:
        log_activity(db, user.id, "create", "property", c["property_id"], detail="افزودن سریع از ملک‌یاب")
    db.commit()
    return {"created": created, "failed": failed}

@router.post("/listings/{listing_id}/convert-to-file")
def convert_to_file(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    if listing.converted_property_id is not None:
        raise HTTPException(400, "این آگهی قبلاً به فایل تبدیل شده")
    if listing.converted_property_id is not None:
        raise HTTPException(400, "این آگهی قبلاً به فایل تبدیل شده")
    _ensure_enriched(db, listing)                     # ← اول جزئیات کامل
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


@router.post("/listings/{listing_id}/assign-neighborhood")
def assign_neighborhood(listing_id: int, data: AssignIn, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """دسته‌بندی دستی آگهی‌های «بدون محله» توسط مشاور."""
    listing = db.get(DiscoveredListing, listing_id)
    if listing is None:
        raise HTTPException(404, "آگهی پیدا نشد")
    if db.get(DiscoveryNeighborhood, data.neighborhood_id) is None:
        raise HTTPException(404, "محله پیدا نشد")
    listing.neighborhood_id = data.neighborhood_id
    db.commit()
    return {"status": "ok"}


@router.get("/subscription")
def get_subscription(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sub = _get_subscription(db, user)
    if not sub:
        return {"allowed_districts": [], "blocked_districts": [], "deal_types": [], "show_unknown": True}
    return {"allowed_districts": sub.allowed_districts or [], "blocked_districts": sub.blocked_districts or [],
            "deal_types": sub.deal_types or [], "show_unknown": sub.show_unknown}


@router.put("/subscription")
def put_subscription(data: SubscriptionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sub = _get_subscription(db, user)
    if not sub:
        sub = DiscoverySubscription(user_id=user.id)
        db.add(sub)
    sub.allowed_districts = data.allowed_districts
    sub.blocked_districts = data.blocked_districts
    sub.deal_types = data.deal_types
    sub.show_unknown = data.show_unknown
    db.commit()
    return {"status": "ok"}