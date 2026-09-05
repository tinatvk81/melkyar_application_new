"""
تنظیمات لاگ سرور — قبلاً فقط خروجی uvicorn روی صفحه‌ی ترمینال بود. اگر سرور
شب یا آخر هفته کرش می‌کرد و کسی پای سیستم نبود، هیچ سابقه‌ای برای بررسی بعدی
نمی‌ماند. حالا همه‌چیز (هم لاگ‌های خودمان، هم لاگ‌های داخلی uvicorn) در یک فایل
با چرخش خودکار (Rotating) هم ذخیره می‌شود.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

MAX_BYTES = 5 * 1024 * 1024  # ۵ مگابایت هر فایل
BACKUP_COUNT = 5  # نگه‌داری ۵ فایل قدیمی چرخشی (در مجموع تا ۳۰ مگابایت)


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # نکته‌ی فنی مهم (که با تست واقعی کشف شد): لاگر "uvicorn.access" به‌طور
    # پیش‌فرض propagate=False دارد — یعنی حتی با اضافه‌کردن handler به root
    # logger، لاگ هر درخواست HTTP اصلاً به فایل ما نمی‌رسید. برای همین این‌جا
    # صریحاً handler را مستقیم به لاگرهای uvicorn هم وصل می‌کنیم. همچنین برای
    # جلوگیری از ثبت دوباره‌ی هر پیام (یک‌بار مستقیم، یک‌بار از طریق propagate
    # به root) صراحتاً propagate را False می‌گذاریم تا هر پیام دقیقاً یک‌بار
    # نوشته شود.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.propagate = False
        uvicorn_logger.addHandler(file_handler)

    return LOG_FILE
