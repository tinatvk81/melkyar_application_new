"""
مسیر فایل‌های همراه برنامه (فونت و...) را درست پیدا می‌کند — چه در حالت
توسعه (اجرای مستقیم main.py) چه بعد از بسته‌بندی با PyInstaller.

نکته‌ی فنی مهم (که با ساخت واقعی یک exe آزمایشی کشف شد): مسیرهای نسبی به
`__file__` داخل ماژول‌هایی مثل ui/styles.py برای پیدا کردن فایل‌های bundle
شده کار نمی‌کنند — چون آن ماژول‌ها از داخل آرشیو فشرده‌ی PyInstaller (نه از
یک فایل واقعی روی دیسک) اجرا می‌شوند و پوشه‌ی «ui» به‌صورت واقعی روی دیسک در
پوشه‌ی موقت اجرا (`sys._MEIPASS`) وجود ندارد؛ یعنی `os.path.join(dirname(__file__), "..", ...)`
از یک پوشه‌ی مجازی/ناموجود عبور می‌کند و فایل واقعی پیدا نمی‌شود. راه‌حل درست:
مسیر را از یک نقطه‌ی ثابت و همیشه‌موجود (ریشه‌ی client/ در حالت توسعه، یا
sys._MEIPASS در حالت frozen) بسازیم، نه از __file__ یک ماژول دلخواه.
"""
import os
import sys


def resource_path(*relative_parts: str) -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # پوشه‌ی موقتی که PyInstaller در آن استخراج می‌کند
    else:
        base = os.path.dirname(os.path.abspath(__file__))  # پوشه‌ی client/
    return os.path.join(base, *relative_parts)
