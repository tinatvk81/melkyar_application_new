from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.follow_up import NotificationRead
from app.services.notification_service import sync_followup_notifications
from app.models.user import User, UserRole as UserRoleEnum
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationRead])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sync_followup_notifications(db, user.id)
    return (db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(50).all())


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sync_followup_notifications(db, user.id)
    n = db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read.is_(False)
    ).count()
    return {"unread": n}


@router.get("/by-user/{user_id}")
def by_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role.value != "admin" and str(user.role) != "admin":
        raise HTTPException(403, "فقط مدیر")
    return (db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.id.desc()).limit(50).all())


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == user.id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.get("/admin-agents")
def admin_agents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """فقط مدیر: فهرست مشاوران برای دیدن اطلاع‌یه‌های آن‌ها."""
    if user.role.value != "admin" and str(user.role) != "admin":
        raise HTTPException(403, "فقط مدیر")
    return [{"id": u.id, "full_name": u.full_name} for u in
            db.query(User).filter(User.role == UserRoleEnum.agent).all()]

