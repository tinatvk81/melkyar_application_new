import re
import time
import logging
from datetime import datetime, timezone

import requests

from .base import SourceAdapter, RawListing

logger = logging.getLogger(__name__)

DIVAR_CITY_IDS = {"mashhad": "3"}
# رهن کامل هم داخل residential-rent است — تشخیصش در parse انجام می‌شود
CATEGORIES = {"residential-sell": "sale", "residential-rent": "rent"}

AGENCY_KEYWORDS = ["مشاور", "املاک", "آژانس", "هلدینگ", "بنگاه", "گروه ساختمانی", "دپارتمان"]
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

_MONEY_RE = re.compile(r"(ودیعه|رهن|اجاره|قیمت کل|قیمت هر متر)\s*:\s*([\d,]+)")
_AREA_RE = re.compile(r"(\d+)\s*متر")
_ROOMS_RE = re.compile(r"(\d+)\s*(?:خواب|اتاق)")
_DISTRICT_RE = re.compile(r"در\s+(.+)$")


def _norm(text: str) -> str:
    return (text or "").translate(_PERSIAN_DIGITS)


def _to_int(s: str) -> int | None:
    digits = s.replace(",", "").strip()
    return int(digits) if digits.isdigit() else None


def _is_probably_agency(text: str) -> bool:
    text = text or ""
    return any(k in text for k in AGENCY_KEYWORDS)


def _parse_prices(mid_text: str) -> tuple[dict, dict]:
    """برچسب‌محور: «اجاره: X» / «ودیعه: X» / «قیمت کل: X» — نه جمع همهٔ ارقام متن."""
    t = _norm(mid_text or "")
    structured = {"price": None, "deposit": None, "monthly_rent": None}
    attrs: dict = {}
    for label, value in _MONEY_RE.findall(t):
        amount = _to_int(value)
        if amount is None:
            continue
        attrs[label] = amount
        if label == "اجاره":
            structured["monthly_rent"] = amount
        elif label in ("ودیعه", "رهن"):
            structured["deposit"] = amount
        elif label == "قیمت کل":
            structured["price"] = amount
    return structured, attrs


def _parse_title(title: str) -> dict:
    t = _norm(title or "")
    area = _AREA_RE.search(t)
    rooms = _ROOMS_RE.search(t)
    return {
        "area_m2": int(area.group(1)) if area else None,
        "rooms": int(rooms.group(1)) if rooms else None,
    }


def _extract_district(row: dict) -> str:
    web = row.get("action", {}).get("payload", {}).get("web_info", {})
    d = web.get("district_persian") or ""
    if d:
        return d
    m = _DISTRICT_RE.search((_norm(row.get("bottom_description_text")) or "").strip())
    return m.group(1).strip() if m else ""


class DivarAdapter(SourceAdapter):
    source_name = "divar"

    def fetch_new(self, city: str, category: str, since: datetime) -> list[RawListing]:
        city_id = DIVAR_CITY_IDS.get(city, "3")
        results: list[RawListing] = []

        for cat_slug, deal_type in CATEGORIES.items():
            payload = {
                "city_ids": [city_id],
                "search_data": {"form_data": {"data": {"category": {"str": {"value": cat_slug}}}}},
                "source_view": "CATEGORY",
                "user_selected_location": {"places": [{"place_id": city_id}]},
            }
            try:
                resp = requests.post(
                    "https://api.divar.ir/v8/postlist/w/search",
                    json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                logger.exception(f"[divar:{cat_slug}] خطا در دریافت — این دسته رد شد")
                continue

            for widget in data.get("list_widgets", []):
                if widget.get("widget_type") != "POST_ROW":
                    continue
                row = widget["data"]
                bottom = row.get("bottom_description_text", "") or ""
                if _is_probably_agency(bottom):
                    continue

                token = row.get("token")
                if not token:
                    continue

                sort_date_str = (widget.get("action_log", {}).get("server_side_info", {})
                                 .get("info", {}).get("sort_date"))
                posted_at = (datetime.fromisoformat(sort_date_str.replace("Z", "+00:00"))
                             if sort_date_str else datetime.now(timezone.utc))
                if posted_at < since:
                    continue

                prices, amounts = _parse_prices(row.get("middle_description_text"))
                title_info = _parse_title(row.get("title"))

                results.append(RawListing(
                    external_id=token,
                    title=row.get("title", ""),
                    raw_address=_extract_district(row),
                    price=prices["price"],
                    deal_type=deal_type,
                    posted_at=posted_at,
                    url=f"https://divar.ir/v/_/{token}",
                    deposit=prices["deposit"],
                    monthly_rent=prices["monthly_rent"],
                    area_m2=title_info["area_m2"],
                    rooms=title_info["rooms"],
                    attributes={"amounts": amounts, "bottom": bottom,
                                "mid": row.get("middle_description_text")},
                ))

            time.sleep(1.5)

        return results