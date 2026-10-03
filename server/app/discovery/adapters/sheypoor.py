"""Adapter شیپور از طریق وب‌سرویس majidapi (غیررسمی — فقط این فایل وابسته است).
سیاست: فقط آگهی‌های شخصی (shopLogo دارد = آژانسی و رد می‌شود)."""
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from .base import SourceAdapter, RawListing

logger = logging.getLogger(__name__)

BASE = "https://api.majidapi.ir/sheypoor"
CITY_ID = "444"              # مشهد
REAL_ESTATE_ROOT = 43603
RATE_SLEEP = 12
_MAX_PAGES = 3
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _token() -> str | None:
    return os.environ.get("MAJIDAPI_TOKEN") or None


def _api(**params) -> dict | None:
    tok = _token()
    if not tok:
        logger.warning("[sheypoor] MAJIDAPI_TOKEN تنظیم نشده — منبع رد شد")
        return None
    params["token"] = tok
    try:
        r = requests.get(BASE, params=params, timeout=25)
        if r.status_code == 429:
            logger.warning("[sheypoor] 429 — 30 ثانیه صبر و تلاش مجدد")
            time.sleep(30)
            r = requests.get(BASE, params=params, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception:
        logger.exception("[sheypoor] خطا در درخواست API")
        return None
    finally:
        time.sleep(RATE_SLEEP)


def _parse_price(price_string: str) -> tuple[int | None, int | None]:
    """برمی‌گرداند (primary, secondary):
    «32,500,000,000 تومان» → (قیمت، None) | «رهن: X / اجاره: Y» → (X, Y) | «رهن: X» → (X, None)"""
    t = (price_string or "").translate(_PERSIAN_DIGITS).strip()
    if not t or "توافقی" in t or "رایگان" in t:
        return None, None
    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]{3,}", t)]
    if not nums:
        return None, None
    if "رهن" in t and "اجاره" in t:
        return nums[0], nums[1]
    if "اجاره" in t:
        return None, nums[0]
    return nums[0], None


def _is_real_estate(it: dict) -> bool:
    return (it.get("category") or {}).get("rootCategoryId") == REAL_ESTATE_ROOT


def _skip_short_term(it: dict) -> bool:
    return "کوتاه مدت" in ((it.get("category") or {}).get("c2") or "")


class SheypoorAdapter(SourceAdapter):
    source_name = "sheypoor"

    def fetch_new(self, city: str, category: str, since: datetime) -> list[RawListing]:
        results: list[RawListing] = []
        for page in range(1, _MAX_PAGES + 1):
            data = _api(action="category", categoryID=REAL_ESTATE_ROOT,
                        cityID=CITY_ID, page=page)
            if not data or not data.get("ok"):
                break
            items = data.get("result") or []
            if not items:
                break
            for it in items:
                if not _is_real_estate(it) or _skip_short_term(it):
                    continue
                if it.get("shopLogo"):      # آژانسی → فقط شخصی می‌خواهیم
                    continue
                posted_at = self._parse_sort(it.get("sortInfo")) or datetime.now(timezone.utc)
                if posted_at < since:
                    continue
                deal_type = self._guess_deal_type(it)
                primary, secondary = _parse_price(it.get("priceString") or "")
                price = deposit = monthly = None
                if deal_type == "sale":
                    price = primary
                elif secondary is not None:
                    deposit, monthly = primary, secondary
                elif primary is not None:
                    deposit = primary        # «رهن: X» بدون اجاره → رهن کامل در convert
                results.append(RawListing(
                    external_id=str(it.get("listingID")),
                    title=it.get("title") or "",
                    raw_address=((it.get("location") or {}).get("neighbourhood") or ""),
                    price=price,
                    deal_type=deal_type,
                    posted_at=posted_at,
                    url=f"https://www.sheypoor.com/v/{it.get('listingID')}",
                    deposit=deposit,
                    monthly_rent=monthly,
                    attributes={"price_string": it.get("priceString"),
                                "c2": (it.get("category") or {}).get("c2")},
                ))
        return results

    @staticmethod
    def _guess_deal_type(it: dict) -> str:
        c2 = (it.get("category") or {}).get("c2") or ""
        if "رهن و اجاره" in c2 or "اجاره" in c2:
            return "rent"        # رهن‌کامل در convert تشخیص داده می‌شود
        return "sale"

    @staticmethod
    def _parse_sort(text: str) -> datetime | None:
        t = (text or "").translate(_PERSIAN_DIGITS).strip()
        if not t:
            return None
        if "لحظات" in t:
            return datetime.now(timezone.utc)
        m = re.search(r"(\d+)\s*(ثانیه|دقیقه|ساعت|روز|هفته|ماه)", t)
        if not m:
            return None
        n, unit = int(m.group(1)), m.group(2)
        mult = {"ثانیه": 1, "دقیقه": 60, "ساعت": 3600, "روز": 86400,
                "هفته": 604800, "ماه": 2592000}[unit]
        return datetime.now(timezone.utc) - timedelta(seconds=n * mult)