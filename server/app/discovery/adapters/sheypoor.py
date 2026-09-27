import re
import json
import logging
import time
from datetime import datetime, timezone

import requests

from .base import SourceAdapter, RawListing

logger = logging.getLogger(__name__)
BASE_URL = "https://www.sheypoor.com"

CATEGORIES = {
    "houses-apartments-for-sale": "sale",
    "villa-for-sale": "sale",
    "house-apartment-for-rent": "rent",
}

AGENCY_KEYWORDS = ["مشاور", "املاک", "آژانس", "دپارتمان", "کارشناس", "بنگاه"]
OWNER_SIGNAL_KEYWORDS = ["دفاتر محترم املاک همکاری نداریم"]
FLIGHT_LINE_RE = re.compile(r'^(\d+):(.*)$', re.MULTILINE)


def _is_probably_agency(item: dict) -> bool:
    attrs = item.get("attributes", {})
    text = f"{attrs.get('title', '')} {attrs.get('description', '')}"
    if any(k in text for k in OWNER_SIGNAL_KEYWORDS):
        return False
    if attrs.get("shopLogo"):
        return True
    return any(k in text for k in AGENCY_KEYWORDS)


def _extract_serp_listings(html_text: str) -> list[dict]:
    listings = []
    for match in FLIGHT_LINE_RE.finditer(html_text):
        try:
            parsed = json.loads(match.group(2))
        except (json.JSONDecodeError, ValueError):
            continue
        listings.extend(_find_serp_items(parsed))
    return listings


def _find_serp_items(node) -> list[dict]:
    found = []
    if isinstance(node, dict):
        qk = node.get("queryKey")
        if isinstance(qk, list) and qk and qk[0] == "LOAD_SERP_RESULTS":
            for page in node.get("state", {}).get("data", {}).get("pages", []):
                for group in page.get("data", []):
                    if group.get("type") == "listingGroup":
                        for item in group.get("items", []):
                            if item.get("type") == "normal":
                                found.append(item)
        for v in node.values():
            found.extend(_find_serp_items(v))
    elif isinstance(node, list):
        for v in node:
            found.extend(_find_serp_items(v))
    return found


def _parse_price(item: dict, deal_type: str) -> int | None:
    def to_int(s):
        if not s or not str(s).replace(",", "").isdigit():
            return None
        return int(str(s).replace(",", ""))

    prices = {p["label"]: p.get("amount") for p in item.get("attributes", {}).get("price") or []}
    if deal_type == "rent":
        return to_int(prices.get("اجاره")) or to_int(prices.get("رهن"))
    return to_int(prices.get("رهن")) or to_int(prices.get("قیمت"))


class SheypoorAdapter(SourceAdapter):
    source_name = "sheypoor"

    def fetch_new(self, city: str, category: str, since: datetime) -> list[RawListing]:
        results: list[RawListing] = []

        for slug, deal_type in CATEGORIES.items():
            url = f"{BASE_URL}/s/{city}/{slug}"
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                resp.raise_for_status()
            except Exception:
                logger.exception(f"[sheypoor:{slug}] خطا در دریافت — این دسته رد شد")
                continue

            for item in _extract_serp_listings(resp.text):
                if _is_probably_agency(item):
                    continue

                attrs = item.get("attributes", {})
                location = attrs.get("location", "")
                district = location.split("، ")[-1] if "، " in location else ""

                sort_ms = (item.get("sort") or [None, None])[1]
                posted_at = (
                    datetime.fromtimestamp(sort_ms / 1000, tz=timezone.utc)
                    if sort_ms else datetime.now(timezone.utc)
                )
                if posted_at < since:
                    continue

                results.append(RawListing(
                    external_id=item.get("id"),
                    title=attrs.get("title", ""),
                    raw_address=district,
                    price=_parse_price(item, deal_type),
                    deal_type=deal_type,
                    posted_at=posted_at,
                    url=attrs.get("url", ""),
                ))

            time.sleep(1.5)

        return results