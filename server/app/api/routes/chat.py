from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.chat_message import ChatMessage
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageIn(BaseModel):
    receiver_id: int
    body: str


@router.get("/contacts")
def contacts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """فهرست مخاطبان: مشاور فقط مدیر؛ مدیر همهٔ کاربران."""
    if user.role.value == "admin" or str(user.role) == "admin":
        rows = db.query(User).filter(User.id != user.id).order_by(User.full_name).all()
    else:
        rows = db.query(User).filter(User.role == "admin").all()
    return [{"id": u.id, "full_name": u.full_name, "username": u.username} for u in rows]


@router.get("/with/{other_id}")
def conversation(other_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(ChatMessage)
            .filter(or_(
                and_(ChatMessage.sender_id == user.id, ChatMessage.receiver_id == other_id),
                and_(ChatMessage.sender_id == other_id, ChatMessage.receiver_id == user.id),
            ))
            .order_by(ChatMessage.id)
            .limit(200).all())
    # پیام‌های ورودی این گفت‌وگو خوانده شوند
    for m in rows:
        if m.receiver_id == user.id and not m.is_read:
            m.is_read = True
    db.commit()
    return [{"id": m.id, "sender_id": m.sender_id, "receiver_id": m.receiver_id,
             "body": m.body, "created_at": m.created_at.isoformat()} for m in rows]


@router.post("/send")
def send(data: MessageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.receiver_id == user.id:
        raise HTTPException(400, "به خودتان پیام نمی‌فرستید")
    other = db.get(User, data.receiver_id)
    if not other:
        raise HTTPException(404, "گیرنده پیدا نشد")
    body = data.body.strip()
    if not body:
        raise HTTPException(400, "متن پیام خالی است")
    m = ChatMessage(sender_id=user.id, receiver_id=data.receiver_id, body=body[:2000])
    db.add(m)
    db.commit()
    db.refresh(m)
    # اطلاع‌یه برای گیرنده (فقط اگر پیام خوانده‌نشده قبلی نداشته باشد تا اسپم نشود)
    unread = db.query(ChatMessage).filter(
        ChatMessage.sender_id == user.id, ChatMessage.receiver_id == data.receiver_id,
        ChatMessage.is_read.is_(False)).count()
    if unread == 1:
        db.add(Notification(user_id=data.receiver_id, title="💬 پیام جدید",
                            body=f"از {user.full_name}: {body[:80]}",
                            entity_type="chat", entity_id=user.id))
        db.commit()
    return {"id": m.id, "created_at": m.created_at.isoformat()}


@router.get("/unread-total")
def unread_total(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.query(ChatMessage).filter(
        ChatMessage.receiver_id == user.id, ChatMessage.is_read.is_(False)).count()
    return {"unread": n}