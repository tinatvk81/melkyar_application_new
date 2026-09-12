from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.properties import _price_expression
from app.db.session import get_db
from app.models.client_request import ClientRequest, RequestStatus
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.client_request import (
    ClientRequestCreate, ClientRequestUpdate, ClientRequestRead,
)
from app.schemas.property import PropertyRead
from app.services.activity_log_service import log_activity

router = APIRouter(prefix="/client-requests", tags=["client-requests"])


def _base(db: Session, user: User):
    """قانون دسترسی: مشاور فقط درخواست‌های خودش؛ مدیر همه."""
    q = db.query(ClientRequest)
    if user.role != UserRole.admin:
        q = q.filter(ClientRequest.owner_agent_id == user.id)
    return q


@router.get("/", response_model=list[ClientRequestRead])
def list_requests(status: Optional[str] = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = _base(db, user)
    if status:
        q = q.filter(ClientRequest.status == RequestStatus(status))
    return q.order_by(ClientRequest.created_at.desc()).all()


@router.post("/", response_model=ClientRequestRead)
def create_request(data: ClientRequestCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    req = ClientRequest(**data.model_dump(), owner_agent_id=user.id)
    db.add(req)
    db.commit()
    db.refresh(req)
    log_activity(db, user.id, "create", "client_request", req.id, detail=req.customer_name)
    return req


@router.put("/{request_id}", response_model=ClientRequestRead)
def update_request(request_id: int, data: ClientRequestUpdate,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    req = _base(db, user).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "درخواست پیدا نشد یا دسترسی ندارید")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "status":
            req.status = RequestStatus(value)
        else:
            setattr(req, field, value)
    db.commit()
    db.refresh(req)
    return req


@router.delete("/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    req = _base(db, user).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "درخواست پیدا نشد یا دسترسی ندارید")
    db.delete(req)
    db.commit()
    return {"ok": True}


@router.get("/{request_id}/matches", response_model=list[PropertyRead])
def request_matches(request_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """
    تطبیق خودکار: فایل‌های فعال منطبق با شرایط درخواست.
    مشاور فقط بین فایل‌های خودش جست‌وجو می‌شود؛ مدیر بین همه‌ی فایل‌ها.
    """
    req = _base(db, user).filter(ClientRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "درخواست پیدا نشد یا دسترسی ندارید")

    q = db.query(Property).filter(Property.status == PropertyStatus.active)
    if user.role != UserRole.admin:
        q = q.filter(Property.owner_agent_id == user.id)

    q = q.filter(Property.deal_type == req.deal_type)
    if req.city:
        q = q.filter(func.lower(Property.city) == func.lower(req.city.strip()))
    if req.district:
        q = q.filter(Property.district.ilike(f"%{req.district.strip()}%"))
    if req.min_area:
        q = q.filter(Property.area_m2 >= req.min_area)
    if req.max_area:
        q = q.filter(Property.area_m2 <= req.max_area)
    if req.min_rooms:
        q = q.filter(Property.rooms >= req.min_rooms)
    if req.max_price:
        q = q.filter(_price_expression() <= req.max_price)

    return q.order_by(Property.created_at.desc()).limit(30).all()