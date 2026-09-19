"""میکرو-مایگریشن استارتاپ — ستون‌های ضروری + تبدیل ستون‌های پولی به NUMERIC بدون سقف."""
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)
REQUIRED_COLUMNS = [
    ("deals", "commission_percent", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
    ("commission_payments", "kind", "VARCHAR(16) NOT NULL DEFAULT 'to_agent'"),
    ("properties", "urgent_until", "DATE"),
    ("properties", "location_url", "VARCHAR(500)"),
]

# ستون‌های پولی: BigInteger سقف ۹.۲×۱۰¹۸ داشت؛ NUMERIC عملاً بی‌نهایت است
MONEY_COLUMNS = [
    ("deals", "deal_amount"),
    ("deals", "commission_amount"),
    ("commission_payments", "amount"),
]


def ensure_critical_columns() -> None:
    with engine.begin() as conn:
        for table, column, definition in REQUIRED_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"))

        for table, column in MONEY_COLUMNS:
            row = conn.execute(
                text("SELECT data_type FROM information_schema.columns "
                     "WHERE table_name = :t AND column_name = :c"),
                {"t": table, "c": column},
            ).first()
            if row is None:
                continue  # جدول هنوز ساخته نشده — alembic مسیر اصلی ساخت است
            if row[0] != "numeric":
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE NUMERIC"))

    logger.info("ستون‌های ضروری تضمین شدند (پول‌ها NUMERIC بدون سقف، percent/kind موجود)")