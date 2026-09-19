"""میکرو-مایگریشن استارتاپ — ستون‌های ضروری + پول‌ها NUMERIC + مقادیر جدید Enum."""
import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    ("deals", "commission_percent", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
    ("commission_payments", "kind", "VARCHAR(16) NOT NULL DEFAULT 'to_agent'"),
    ("properties", "urgent_until", "DATE"),
    ("properties", "location_url", "VARCHAR(500)"),
    ("deals", "agent2_id", "INTEGER"),
    ("deals", "commission_percent_agent2", "DOUBLE PRECISION"),
]

MONEY_COLUMNS = [
    ("deals", "deal_amount"),
    ("deals", "commission_amount"),
    ("commission_payments", "amount"),
]

# نوع Enum در Postgres به‌صورت پویا پیدا می‌شود (به نام کلاس وابسته نیستیم)
NEW_ENUM_VALUES = [
    ("client_requests", "status", ["contacted", "visited", "negotiation", "won", "lost"]),
    ("properties", "status", ["rented"]),
]


def _add_enum_values(conn):
    for table, column, values in NEW_ENUM_VALUES:
        row = conn.execute(
            text("SELECT udt_name FROM information_schema.columns "
                 "WHERE table_name = :t AND column_name = :c"),
            {"t": table, "c": column},
        ).first()
        if not row:
            continue
        for v in values:
            conn.execute(text(f"ALTER TYPE {row[0]} ADD VALUE IF NOT EXISTS '{v}'"))


def ensure_critical_columns() -> None:
    with engine.begin() as conn:
        for table, column, definition in REQUIRED_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"))

        _add_enum_values(conn)

        for table, column in MONEY_COLUMNS:
            row = conn.execute(
                text("SELECT data_type FROM information_schema.columns "
                     "WHERE table_name = :t AND column_name = :c"),
                {"t": table, "c": column},
            ).first()
            if row is None:
                continue
            if row[0] != "numeric":
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE NUMERIC"))

    logger.info("ستون‌های ضروری تضمین شدند — پول‌ها NUMERIC، Enumها به‌روز")