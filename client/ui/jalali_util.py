"""تبدیل تاریخ میلادیِ رشته‌ای (yyyy-mm-dd) به شمسی برای «نمایش» —
دیتابیس و API همیشه میلادی می‌مانند؛ فقط نمایش شمسی می‌شود."""
import jdatetime


def to_jalali_str(value, with_time: bool = False) -> str:
    """ورودی: 'yyyy-mm-dd' یا 'yyyy-mm-ddTHH:MM' یا datetime iso — خروجی شمسی."""
    if not value:
        return "—"
    s = str(value)
    try:
        date_part = s[:10]
        y, m, d = (int(x) for x in date_part.split("-"))
        j = jdatetime.date.fromgregorian(date=__import__("datetime").date(y, m, d))
        out = f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        if with_time and len(s) >= 16 and "T" in s:
            out += f" — {s[11:16]}"
        return out
    except Exception:
        return s  # اگر فرمت عجیب بود، همانی که بود نشان بده