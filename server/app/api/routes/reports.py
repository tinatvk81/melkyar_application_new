import io
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.routes.properties import _base_query, apply_filters, _build_order_clause
from app.db.session import get_db
from app.models.activity_log import ActivityLog
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


@router.get("/reports/dashboard")
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    خلاصه‌ی آماری برای تب «داشبورد». برای مشاور فقط آمار خودش، برای مدیر آمار
    کل دفتر (به‌علاوه‌ی چند شاخص فقط-مدیر مثل تعداد مشاوران و فعالیت امروز).
    """
    base = _base_query(db, current_user, status=PropertyStatus.active)

    total_active = base.count()

    by_deal_type_rows = (
        _base_query(db, current_user, status=PropertyStatus.active)
        .with_entities(Property.deal_type, func.count(Property.id))
        .group_by(Property.deal_type)
        .all()
    )
    by_deal_type = {dt.value if hasattr(dt, "value") else dt: count for dt, count in by_deal_type_rows}

    today = date.today()
    urgent_cutoff = today + timedelta(days=7)
    normal_cutoff = today + timedelta(days=30)

    urgent_renewals = (
        _base_query(db, current_user, status=PropertyStatus.active)
        .filter(Property.contract_end_date.isnot(None), Property.contract_end_date <= urgent_cutoff)
        .count()
    )
    upcoming_renewals = (
        _base_query(db, current_user, status=PropertyStatus.active)
        .filter(Property.contract_end_date.isnot(None), Property.contract_end_date <= normal_cutoff)
        .count()
    )

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_this_week = (
        _base_query(db, current_user, status=PropertyStatus.active)
        .filter(Property.created_at >= seven_days_ago)
        .count()
    )

    result = {
        "total_active": total_active,
        "by_deal_type": by_deal_type,
        "urgent_renewals": urgent_renewals,
        "upcoming_renewals": upcoming_renewals,
        "new_this_week": new_this_week,
    }

    if current_user.role == UserRole.admin:
        result["total_agents"] = db.query(User).filter(User.role == UserRole.agent).count()
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result["activity_today"] = db.query(ActivityLog).filter(ActivityLog.created_at >= today_start).count()

    return result


@router.post("/reports/trigger-sms-reminders")
def trigger_sms_reminders(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """
    فقط برای مدیر: اجرای دستیِ فوری کارِ یادآوری پیامکی، بدون نیاز به منتظر
    ماندن تا زمان‌بند روزانه (ساعت ۹ صبح). مفید برای تست تنظیمات پیامک یا
    یک یادآوری فوری خارج از برنامه‌ی معمول.
    """
    from app.services.reminder_job import run_daily_reminder_job
    return run_daily_reminder_job(db)
