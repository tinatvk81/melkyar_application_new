# server/app/discovery/jobs/scheduler.py
import logging
import time
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.discovery.adapters.divar import DivarAdapter
from app.discovery.adapters.sheypoor import SheypoorAdapter
from app.discovery.services.matcher import match_neighborhood
from app.discovery.services.dedupe import upsert_listing

logger = logging.getLogger(__name__)

ADAPTERS = [DivarAdapter(), SheypoorAdapter()]
POLL_INTERVAL_SECONDS = 600


def run_one_source(adapter, db):
    try:
        since = datetime.now(timezone.utc) - timedelta(days=14)  # موقت برای تست اول
        raw_listings = adapter.fetch_new(city="mashhad", category="real-estate", since=since)
        new_count = 0
        for raw in raw_listings:
            neighborhood_id = match_neighborhood(raw.raw_address or raw.title, db)
            was_new = upsert_listing(db, {
                "source": adapter.source_name,
                "external_id": raw.external_id,
                "title": raw.title,
                "raw_address": raw.raw_address,
                "city": city,
                "price": raw.price,
                "deposit": raw.deposit,
                "monthly_rent": raw.monthly_rent,
                "area_m2": raw.area_m2,
                "rooms": raw.rooms,
                "deal_type": raw.deal_type,
                "neighborhood_id": neighborhood_id,
                "url": raw.url,
                "attributes": raw.attributes,
                "posted_at": raw.posted_at,
                "fetched_at": datetime.now(timezone.utc),
            })
            if was_new:
                new_count += 1
        logger.info(f"[{adapter.source_name}] {new_count} آگهی جدید از {len(raw_listings)} دریافتی")
    except Exception:
        logger.exception(f"[{adapter.source_name}] خطا در دریافت — این منبع رد شد، بقیه ادامه می‌دن")


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