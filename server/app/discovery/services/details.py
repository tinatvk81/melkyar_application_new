"""دریافت جزئیات هر آگهی دیوار (بدون شماره تماس — آن پشت honeypot است و عمداً اتومات نمی‌گیریم)."""
import logging

import requests

from app.discovery.services.keywords import extract_amenities, parse_fa_amount

logger = logging.getLogger(__name__)

DETAILS_URL = "https://api.divar.ir/v8/posts-v2/web/{token}"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_details(token: str) -> dict | None:
    try:
        r = requests.get(DETAILS_URL.format(token=token), headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        logger.exception(f"[details] خطا در دریافت جزئیات {token}")
        return None


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def enrich_from_payload(listing, payload: dict) -> None:
    """استخراج دفاعی: ردیف‌های title/value، توضیحات، ویژگی‌ها — بدون وابستگی به فرمت دقیق."""
    rows, features, description = [], [], ""
    for w in _walk(payload.get("sections") or []):
        wt = w.get("widget_type") or ""
        data = w.get("data") or {}
        if wt == "DESCRIPTION_ROW" and not description:
            description = (data.get("text") or "").strip()
        elif "FEATURE" in wt or "AMENIT" in wt:
            t = (data.get("title") or "").strip()
            if t:
                features.append(t)
        if isinstance(data.get("title"), str) and isinstance(data.get("value"), str):
            rows.append((data["title"], data["value"]))
        if isinstance(data.get("items"), list):
            for it in data["items"]:
                if isinstance(it, dict) and isinstance(it.get("title"), str) and isinstance(it.get("value"), str):
                    rows.append((it["title"], it["value"]))

    attrs = dict(listing.attributes or {})

    def row_value(*keys):
        for title, value in rows:
            if any(k in title for k in keys):
                return value
        return None

    if listing.area_m2 is None:
        v = row_value("متراژ")
        if v and v.strip().isdigit():
            listing.area_m2 = int(v.strip())
    if listing.rooms is None:
        v = row_value("اتاق", "خواب")
        if v and v.strip().isdigit():
            listing.rooms = int(v.strip())
    if "build_year" not in attrs:
        v = row_value("ساخت")
        if v and v.strip().isdigit():
            attrs["build_year"] = int(v.strip())
    v = row_value("طبقه")
    if v:
        attrs["floor"] = v

    # ودیعه/اجارهٔ قابل‌تبدیل (اگهی اجارهٔ بدون قیمت در لیست)
    if listing.deal_type == "rent":
        dep = row_value("ودیعه")
        rent = row_value("اجاره")
        if listing.deposit is None and dep:
            listing.deposit = parse_fa_amount(dep)
        if listing.monthly_rent is None and rent:
            listing.monthly_rent = parse_fa_amount(rent)

    kw_hits = extract_amenities(description, listing.title or "", listing.raw_address or "")
    amenities = sorted(set(features) | set(kw_hits))
    if amenities:
        attrs["amenities"] = amenities
    if description:
        attrs["description"] = description
    attrs["details_rows"] = rows
    attrs["has_details"] = True

    listing.attributes = attrs