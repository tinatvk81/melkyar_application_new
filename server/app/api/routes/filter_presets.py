from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.filter_preset import FilterPreset
from app.models.notification import Notification
from app.models.user import User, UserRole

router = APIRouter(prefix="/filter-presets", tags=["filter-presets"])


class PresetIn(BaseModel):
    name: str
    params: dict


@router.get("/")
def list_presets(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return [{"id": p.id, "name": p.name, "params": p.params}
            for p in db.query(FilterPreset)
            .filter(FilterPreset.approved.is_(True), FilterPreset.pending_delete.is_(False))
            .order_by(FilterPreset.id).all()]

@router.get("/pending")
def pending_additions(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    rows = (db.query(FilterPreset, User.full_name)
            .join(User, FilterPreset.requested_by == User.id)
            .filter(FilterPreset.approved.is_(False)).all())
    return [{"id": p.id, "name": p.name, "params": p.params, "requester": fn} for p, fn in rows]


@router.get("/delete-requests")
def pending_deletions(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    rows = (db.query(FilterPreset, User.full_name)
            .join(User, FilterPreset.requested_by == User.id)
            .filter(FilterPreset.pending_delete.is_(True)).all())
    return [{"id": p.id, "name": p.name, "params": p.params, "requester": fn} for p, fn in rows]

@router.post("/")
def create_preset(data: PresetIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = FilterPreset(name=data.name.strip(), params=data.params, requested_by=user.id,
                     approved=(user.role == UserRole.admin))
    db.add(p)
    db.commit()
    db.refresh(p)
    if not p.approved:
        for a in db.query(User).filter(User.role == UserRole.admin).all():
            db.add(Notification(user_id=a.id, title="پیشنهاد فیلتر آمادهٔ جدید",
                                body=f"«{p.name}» توسط {user.full_name} پیشنهاد شده — در مدیریت فیلترها تأیید کن.",
                                entity_type="preset", entity_id=p.id))
        db.commit()
    return {"id": p.id, "approved": p.approved}


@router.post("/{preset_id}/approve")
def approve(preset_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(FilterPreset, preset_id)
    if not p:
        raise HTTPException(404, "پیدا نشد")
    p.approved = True
    db.commit()
    return {"ok": True}


@router.post("/{preset_id}/request-delete")
def request_delete(preset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """مشاور درخواست حذف می‌دهد → اطلاع‌یه به مدیر. مدیر در پنل، تأیید می‌کند."""
    p = db.get(FilterPreset, preset_id)
    if not p:
        raise HTTPException(404, "پیدا نشد")
    if p.pending_delete:
        return {"ok": True}  # قبلاً درخواست داده
    p.pending_delete = True
    for a in db.query(User).filter(User.role == UserRole.admin).all():
        db.add(Notification(user_id=a.id, title="درخواست حذف فیلتر آماده",
                            body=f"«{p.name}» توسط {user.full_name} درخواست حذف داده — در مدیریت فیلترها تأیید کن.",
                            entity_type="preset_delete", entity_id=p.id))
    db.commit()
    return {"ok": True}


@router.post("/{preset_id}/approve-delete")
def approve_delete(preset_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(FilterPreset, preset_id)
    if not p:
        raise HTTPException(404, "پیدا نشد")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/{preset_id}/reject-delete")
def reject_delete(preset_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(FilterPreset, preset_id)
    if not p:
        raise HTTPException(404, "پیدا نشد")
    p.pending_delete = False
    db.commit()
    return {"ok": True}


@router.delete("/{preset_id}")
def delete_preset(preset_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(FilterPreset, preset_id)
    if not p:
        raise HTTPException(404, "پیدا نشد")
    db.delete(p)
    db.commit()
    return {"ok": True}