"""بکاپ دیتابیس به‌شکل JSON فشرده — بدون نیاز به pg_dump (کلاینت پستگرس در ایمیج نیست).
هر شب ۰۲:۳۰ خودکار + دستی توسط مدیر؛ ۱۴ نسخهٔ آخر در media/backups نگه‌داری می‌شود."""
import gzip
import json
import os
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

BACKUP_DIR = os.path.join("media", "backups")
KEEP = 14
TABLES = ["users", "properties", "property_images", "deals", "commission_payments",
          "client_requests", "follow_ups", "notifications", "activity_logs",
          "chat_messages", "bot_faqs", "filter_presets"]


def build_backup_bytes() -> bytes:
    db = SessionLocal()
    try:
        tables = {}
        for t in TABLES:
            try:
                rows = db.execute(text(f"SELECT * FROM {t}")).mappings().all()
                tables[t] = [dict(r) for r in rows]
            except Exception:
                tables[t] = None  # جدول موجود نیست — رد شود
        meta = {"created_at": datetime.now(timezone.utc).isoformat(),
                "app_version": settings.APP_VERSION}
        payload = json.dumps({"meta": meta, "tables": tables},
                             default=str, ensure_ascii=False)
        return gzip.compress(payload.encode("utf-8"))
    finally:
        db.close()


def backup_dir() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def prune(keep: int = KEEP) -> None:
    files = sorted(f for f in os.listdir(backup_dir()) if f.endswith(".json.gz"))
    for f in files[:-keep]:
        try:
            os.remove(os.path.join(backup_dir(), f))
        except OSError:
            pass