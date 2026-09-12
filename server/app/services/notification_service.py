from datetime import date

from sqlalchemy.orm import Session

from app.models.follow_up import FollowUp, FollowUpStatus
from app.models.notification import Notification


def sync_followup_notifications(db: Session, user_id: int):
    """
    برای پیگیری‌های سررسید‌گذشته/امروز که هنوز اطلاع‌یه نداشته‌اند، یک اطلاع‌یه می‌سازد
    (فقط یک‌بار برای هر پیگیری — با فلگ reminded). با هر باز شدن زنگ یا شمارنده اجرا می‌شود.
    """
    today = date.today()
    dues = db.query(FollowUp).filter(
        FollowUp.user_id == user_id,
        FollowUp.status == FollowUpStatus.pending,
        FollowUp.reminded.is_(False),
        FollowUp.due_date.isnot(None),
        FollowUp.due_date <= today,
    ).all()
    for fu in dues:
        overdue = fu.due_date < today
        db.add(Notification(
            user_id=user_id,
            title="⚠️ پیگیری عقب‌افتاده!" if overdue else "📌 پیگیری برای امروز",
            body=f"{fu.title} — سررسید: {fu.due_date}",
            entity_type="follow_up", entity_id=fu.id,
        ))
        fu.reminded = True
    if dues:
        db.commit()