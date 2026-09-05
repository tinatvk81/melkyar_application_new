import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.routes.properties import _base_query, apply_filters, _build_order_clause
from app.db.session import get_db
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.property import PropertyRead
from app.services.excel_export import build_properties_excel
from app.services.pdf_export import build_properties_pdf, build_agent_performance_pdf

router = APIRouter(tags=["reports"])


def _accessible_properties(db: Session, current_user: User, sort_by=None, sort_order=None, **filters):
    """
    از همان تابع apply_filters که در properties.py برای فهرست اصلی استفاده می‌شود
    این‌جا هم استفاده می‌شود — تا خروجی PDF/اکسل دقیقاً همان چیزی باشد که کاربر
    با فیلترهایش روی صفحه می‌بیند، نه یک منطق جدا که ممکن است با آن ناهماهنگ شود.
    مرتب‌سازی هم به همین دلیل با همان منطق فهرست اصلی هماهنگ شده است.
    """
    q = _base_query(db, current_user)
    q = apply_filters(q, **filters)
    order_clause = _build_order_clause(sort_by, sort_order)
    return q.order_by(order_clause).all()


@router.get("/properties/export/pdf")
def export_properties_pdf(
    city: Optional[str] = None,
    district: Optional[str] = None,
    deal_type: Optional[str] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_rooms: Optional[int] = None,
    has_elevator: Optional[bool] = None,
    has_parking: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    properties = _accessible_properties(
        db, current_user, sort_by=sort_by, sort_order=sort_order,
        city=city, district=district, deal_type=deal_type, min_area=min_area,
        max_area=max_area, min_rooms=min_rooms, has_elevator=has_elevator, has_parking=has_parking,
        min_price=min_price, max_price=max_price, search=search,
    )
    data = [PropertyRead.model_validate(p).model_dump(mode="json") for p in properties]
    pdf_bytes = build_properties_pdf(data)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=properties-export.pdf"},
    )


@router.get("/properties/export/excel")
def export_properties_excel(
    city: Optional[str] = None,
    district: Optional[str] = None,
    deal_type: Optional[str] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    min_rooms: Optional[int] = None,
    has_elevator: Optional[bool] = None,
    has_parking: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    properties = _accessible_properties(
        db, current_user, sort_by=sort_by, sort_order=sort_order,
        city=city, district=district, deal_type=deal_type, min_area=min_area,
        max_area=max_area, min_rooms=min_rooms, has_elevator=has_elevator, has_parking=has_parking,
        min_price=min_price, max_price=max_price, search=search,
    )
    data = [PropertyRead.model_validate(p).model_dump(mode="json") for p in properties]
    excel_bytes = build_properties_excel(data)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=properties-export.xlsx"},
    )


@router.get("/reports/agent-performance")
def agent_performance(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """فقط برای مدیر: تعداد فایل هر مشاور، تفکیک بر اساس نوع معامله، و تعداد ۳۰ روز اخیر."""
    rows = (
        db.query(User.id, User.full_name, User.username, Property.deal_type, func.count(Property.id))
        .join(Property, Property.owner_agent_id == User.id)
        .filter(Property.status == PropertyStatus.active)
        .group_by(User.id, User.full_name, User.username, Property.deal_type)
        .all()
    )

    agents: dict[int, dict] = {}
    for user_id, full_name, username, deal_type, count in rows:
        agent = agents.setdefault(user_id, {
            "user_id": user_id, "full_name": full_name, "username": username,
            "total": 0, "by_deal_type": {}, "last_30_days": 0,
        })
        deal_type_value = deal_type.value if hasattr(deal_type, "value") else deal_type
        agent["by_deal_type"][deal_type_value] = count
        agent["total"] += count

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_rows = (
        db.query(User.id, func.count(Property.id))
        .join(Property, Property.owner_agent_id == User.id)
        .filter(Property.status == PropertyStatus.active, Property.created_at >= thirty_days_ago)
        .group_by(User.id)
        .all()
    )
    recent_map = dict(recent_rows)
    for user_id, agent in agents.items():
        agent["last_30_days"] = recent_map.get(user_id, 0)

    # مشاورانی که هنوز هیچ فایلی ثبت نکرده‌اند هم با صفر نمایش داده شوند
    all_agents = db.query(User).filter(User.role == UserRole.agent).all()
    for u in all_agents:
        agents.setdefault(u.id, {
            "user_id": u.id, "full_name": u.full_name, "username": u.username,
            "total": 0, "by_deal_type": {}, "last_30_days": 0,
        })

    return list(agents.values())


@router.get("/reports/agent-performance/pdf")
def agent_performance_pdf(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    agents_data = agent_performance(db=db, _admin=_admin)
    pdf_bytes = build_agent_performance_pdf(agents_data)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=agent-performance-report.pdf"},
    )
