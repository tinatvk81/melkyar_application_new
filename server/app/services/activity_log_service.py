from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def log_activity(
    db: Session,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    detail: str | None = None,
):
    """
    یک ردیف تاریخچه ثبت می‌کند. این تابع commit خودش را انجام می‌دهد (مستقل از
    تراکنش اصلی) چون ثبت لاگ یک عملیات جانبی است، نه بخشی حیاتی از عملیات اصلی —
    حتی اگر ثبت لاگ به هر دلیلی با خطا مواجه شود، نباید عملیات اصلی (که قبلاً
    commit شده) را تحت تاثیر قرار دهد.
    """
    entry = ActivityLog(
        user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, detail=detail
    )
    db.add(entry)
    db.commit()
