"""استخراج ویژگی‌ها/امکانات از متن آگهی (توضیحات + عنوان) با کلمات کلیدی."""
import re

_ZWNJ = "\u200c"
AMENITY_KEYWORDS = [
    "آسانسور", "پارکینگ", "انباری", "روف گاردن", "بالکن", "حیاط", "استخر", "سونا",
    "جکوزی", "سالن ورزش", "مبله", "بازسازی", "کولر گازی", "پکیج", "رادیاتور",
    "کولر آبی", "نورگیر", "لابی", "نگهبانی", "درب ضد سرقت", "آشپزخانه اپن",
    "کابینت", "سرامیک", "پارکت", "نوساز", "بدون واسطه", "مترو", "دو پارکینگ",
    "فول امکانات", "سند تک برگ", "تک مالک",
]

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _normalize(text: str) -> str:
    t = (text or "").translate(_FA_DIGITS)
    t = t.replace(_ZWNJ, " ").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", t)


def extract_amenities(*texts: str) -> list[str]:
    hay = _normalize(" ".join(t for t in texts if t))
    found = []
    for kw in AMENITY_KEYWORDS:
        if _normalize(kw) in hay and kw not in found:
            found.append(kw)
    return found


def parse_fa_amount(text: str):
    """«۱.۷۰۰ میلیارد» → 1_700_000_000 | «۶ میلیون» → 6_000_000 | «رایگان» → 0"""
    t = _normalize(text or "").replace(",", "").strip()
    if not t:
        return None
    if "رایگان" in t:
        return 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(میلیارد|میلیون|تومان)?", t)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2) or "تومان"
    if unit == "میلیارد":
        val *= 1_000_000_000
    elif unit == "میلیون":
        val *= 1_000_000
    return int(val)