import logging

from app.core.logging_config import setup_logging
log_file_path = setup_logging()
logger = logging.getLogger(__name__)
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.routes import (
    auth, properties, users, version, import_excel, property_images,
    reports, activity_logs, deals, client_requests, follow_ups,
    notifications, filter_presets, chat, bot, installers, backups,
)
app = FastAPI(
    title="سامانه‌ی مدیریت فایل‌های ملکی",
    # مستندات خودکار API فقط در حالت توسعه (DEBUG=true در .env) فعال است —
    # در محیط عملیاتی، غیرفعال کردن این‌ها یعنی ساختار کامل endpointها/مدل‌ها
    # بدون نیاز به لاگین روی شبکه‌ی دفتر قابل مرور نیست.
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
# app = FastAPI(
#     title="سامانه‌ی مدیریت فایل‌های ملکی",
#     docs_url="/docs",
#     redoc_url="/redoc",
#     openapi_url="/openapi.json",
# )
app.include_router(bot.router)
app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(property_images.router)
app.include_router(import_excel.router)
app.include_router(reports.router)
app.include_router(activity_logs.router)
app.include_router(users.router)
app.include_router(version.router)
app.include_router(deals.router)
app.include_router(client_requests.router)
app.include_router(follow_ups.router)
app.include_router(notifications.router)
app.include_router(filter_presets.router)
app.include_router(chat.router)
app.include_router(installers.router)
app.include_router(backups.router)
# پوشه‌ای که نصب‌کننده‌های exe نسخه‌های جدید در آن قرار می‌گیرند (بخش ۸ روادمپ)
app.mount("/static-installers", StaticFiles(directory="static_installers"), name="static-installers")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    قبلاً یک خطای پیش‌بینی‌نشده (باگ ناشناخته، خرابی اتصال دیتابیس و...) فقط در
    ترمینال (اگر کسی نگاه می‌کرد) نمایش داده می‌شد و کلاینت یک پاسخ خام و گنگ
    می‌گرفت. حالا: کل traceback در فایل لاگ ثبت می‌شود (برای بررسی بعدی)، و
    کلاینت یک پیام تمیز و فارسی می‌گیرد، نه جزئیات داخلی سرور.
    """
    logger.exception(f"خطای پیش‌بینی‌نشده در {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "خطای غیرمنتظره‌ای در سرور رخ داد. اگر این خطا تکرار شد، فایل لاگ سرور را بررسی کنید."},
    )


@app.on_event("startup")
def on_startup():
    logger.info(f"سرور راه‌اندازی شد — نسخه {settings.APP_VERSION} — فایل لاگ: {log_file_path}")

    try:
        from app.db.ensure_columns import ensure_critical_columns
        ensure_critical_columns()
    except Exception:
        # اگر هنوز دیتابیس/جدول‌ها ساخته نشده‌اند، اجازه بده سرور بالا بیاید؛
        # alembic upgrade head همچنان مسیر اصلی ساخت جدول‌هاست.
        logger.exception("بررسی/افزودن ستون‌های ضروری ناموفق بود")

    if settings.SMS_ENABLED:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.db.session import SessionLocal
        from app.services.reminder_job import run_daily_reminder_job

        def scheduled_job():
            db = SessionLocal()
            try:
                result = run_daily_reminder_job(db)
                logger.info(f"کارِ یادآوری روزانه‌ی پیامکی اجرا شد: {result}")
            finally:
                db.close()

        scheduler = BackgroundScheduler(timezone="Asia/Tehran")
        scheduler.add_job(scheduled_job, "cron", hour=9, minute=0)
        scheduler.start()
        logger.info("زمان‌بند یادآوری پیامکی فعال شد (هر روز ساعت ۹ صبح)")

    # --- بکاپ خودکار شبانه (مستقل از SMS) ---
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.services.backup_service import build_backup_bytes, backup_dir, prune
    import os as _os

    def _nightly_backup():
        name = f"melkyar-{datetime.now().strftime('%Y%m%d-%H%M')}.json.gz"
        try:
            with open(_os.path.join(backup_dir(), name), "wb") as f:
                f.write(build_backup_bytes())
            prune()
            logger.info(f"بکاپ شبانه ساخته شد: {name}")
        except Exception:
            logger.exception("بکاپ شبانه ناموفق بود")

    _bs = BackgroundScheduler(timezone="Asia/Tehran")
    _bs.add_job(_nightly_backup, "cron", hour=2, minute=30)
    _bs.start()
    logger.info("بکاپ خودکار شبانه فعال شد (هر روز ۰۲:۳۰)")

@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


# اجرا: uvicorn app.main:app --host 0.0.0.0 --port 8000
