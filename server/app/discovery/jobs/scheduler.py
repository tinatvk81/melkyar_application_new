import logging
import time
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from sqlalchemy import or_
from app.db.session import SessionLocal
from app.discovery.adapters.divar import DivarAdapter
from app.discovery.adapters.sheypoor import SheypoorAdapter
from app.discovery.services.matcher import match_neighborhood
from app.discovery.services.dedupe import upsert_listing
from app.discovery.services.details import fetch_details, enrich_from_payload
from app.discovery.models.listing import DiscoveredListing

logger = logging.getLogger(__name__)

ADAPTERS = [DivarAdapter(), SheypoorAdapter()]
CITY = "mashhad"
POLL_INTERVAL_SECONDS = 600
DETAILS_PER_CYCLE = 40
DETAIL_SLEEP = 1.2


def _enrich_one(db, listing) -> bool:
    payload = fetch_details(listing.external_id)
    if not payload:
        return False
    enrich_from_payload(listing, payload)
    db.commit()
    return True


def run_one_source(adapter, db):
    try:
        since = datetime.now(timezone.utc) - timedelta(minutes=35)
        raw_listings = adapter.fetch_new(city=CITY, category="real-estate", since=since)
        new_keys = []
        for raw in raw_listings:
            neighborhood_id = match_neighborhood(raw.raw_address or raw.title, db)
            was_new = upsert_listing(db, {
                "source": adapter.source_name, "external_id": raw.external_id,
                "title": raw.title, "raw_address": raw.raw_address, "city": CITY,
                "price": raw.price, "deposit": raw.deposit, "monthly_rent": raw.monthly_rent,
                "area_m2": raw.area_m2, "rooms": raw.rooms, "deal_type": raw.deal_type,
                "neighborhood_id": neighborhood_id, "url": raw.url,
                "attributes": raw.attributes, "posted_at": raw.posted_at,
                "fetched_at": datetime.now(timezone.utc),
            })
            if was_new:
                new_keys.append((adapter.source_name, raw.external_id))
        logger.info(f"[{adapter.source_name}] {len(new_keys)} آگهی جدید از {len(raw_listings)} دریافتی")

        done = 0
        for src, ext in new_keys:
            if done >= DETAILS_PER_CYCLE:
                logger.info(f"[{src}] سقف جزئیات این چرخه پر شد")
                break
            row = db.query(DiscoveredListing).filter_by(source=src, external_id=ext).first()
            if row and _enrich_one(db, row):
                done += 1
            time.sleep(DETAIL_SLEEP)
    except Exception:
        db.rollback()
        logger.exception(f"[{adapter.source_name}] خطا — منبع رد شد")


def backfill_details(limit=300):
    """آگهی‌هایی که هنوز جزئیات نگرفته‌اند (has_details در attributes نیست)."""
    db = SessionLocal()
    try:
        rows = (db.query(DiscoveredListing)
                .filter(or_(DiscoveredListing.attributes.is_(None),
                            ~DiscoveredListing.attributes.has_key("has_details")))
                .order_by(DiscoveredListing.posted_at.desc())
                .limit(limit).all())
        ok = 0
        for r in rows:
            if _enrich_one(db, r):
                ok += 1
            time.sleep(DETAIL_SLEEP)
        print(f"enriched {ok}/{len(rows)}")
    finally:
        db.close()


def main_loop():
    while True:
        db = SessionLocal()
        try:
            for adapter in ADAPTERS:
                run_one_source(adapter, db)
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main_loop()