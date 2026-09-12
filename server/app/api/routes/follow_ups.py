from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.follow_up import FollowUp, FollowUpStatus
from app.models.user import User, UserRole
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate, FollowUpRead
from app.services.activity_log_service import log_activity

router = APIRouter(prefix="/follow-ups", tags=["follow-ups"])


def _base(db: Session, user: User):
    q = db.query(FollowUp)
    if user.role != UserRole.admin:
        q = q.filter(FollowUp.user_id == user.id)
    return q


@router.get("/", response_model=list[FollowUpRead])
def list_follow_ups(when: str = "all", db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    q = _base(db, user)
    today = date.today()
    if when == "overdue":
        q = q.filter(FollowUp.status == FollowUpStatus.pending,
                     FollowUp.due_date.isnot(None), FollowUp.due_date < today)
    elif when == "today":
        q = q.filter(FollowUp.status == FollowUpStatus.pending, FollowUp.due_date == today)
    elif when == "upcoming":
        q = q.filter(FollowUp.status == FollowUpStatus.pending,
                     FollowUp.due_date.isnot(None), FollowUp.due_date > today)
    elif when == "done":
        q = q.filter(FollowUp.status == FollowUpStatus.done)
    return q.order_by(FollowUp.due_date.asc().nulls_last(), FollowUp.due_time.asc().nulls_last(), FollowUp.id.desc()).all()


@router.post("/", response_model=FollowUpRead)
def create_follow_up(data: FollowUpCreate, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    fu = FollowUp(**data.model_dump(), user_id=user.id)
    db.add(fu)
    db.commit()
    db.refresh(fu)
    log_activity(db, user.id, "create", "follow_up", fu.id, detail=fu.title)
    return fu


def _get_own(db: Session, user: User, fid: int) -> FollowUp:
    q = _base(db, user).filter(FollowUp.id == fid)
    fu = q.first()
    if not fu:
        raise HTTPException(404, "پیگیری پیدا نشد یا دسترسی ندارید")
    return fu


@router.put("/{follow_up_id}", response_model=FollowUpRead)
def update_follow_up(follow_up_id: int, data: FollowUpUpdate,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fu = _get_own(db, user, follow_up_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "status":
            fu.status = FollowUpStatus(value)
            if value == "done":
                fu.done_at = datetime.now(timezone.utc)
        else:
            setattr(fu, field, value)
    db.commit()
    db.refresh(fu)
    return fu


@router.post("/{follow_up_id}/done", response_model=FollowUpRead)
def mark_done(follow_up_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    fu = _get_own(db, user, follow_up_id)
    fu.status = FollowUpStatus.done
    fu.done_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fu)
    return fu


@router.delete("/{follow_up_id}")
def delete_follow_up(follow_up_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    fu = _get_own(db, user, follow_up_id)
    db.delete(fu)
    db.commit()
    return {"ok": True}