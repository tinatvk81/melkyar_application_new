from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, Float
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate, PropertyListResponse

router = APIRouter(prefix="/properties", tags=["properties"])


def _base_query(db: Session, current_user: User):
    q = db.query(Property).filter(Property.status == PropertyStatus.active)
    # --- قانون کلیدی دسترسی: این فیلتر در لایه‌ی سرور اجرا می‌شود، نه در UI ---
    # مشاور فقط فایل‌های خودش را می‌بیند؛ مدیر همه را می‌بیند.
    if current_user.role != UserRole.admin:
        q = q.filter(Property.owner_agent_id == current_user.id)
    return q


def _price_expression():
    """
    مبلغ داخل ستون JSONB «details» ذخیره شده و اسمش بسته به نوع معامله فرق دارد
    (price برای فروش، total_price برای پیش‌خرید، deposit_full برای رهن‌کامل،
    monthly_rent برای اجاره). این تابع یک عبارت SQL می‌سازد که هرکدام که برای آن
    ردیف موجود باشد را به‌عنوان «مبلغ» برای فیلتر بازه‌ی قیمت استفاده می‌کند.
    """
    return func.coalesce(
        Property.details["price"].astext.cast(Float),
        Property.details["total_price"].astext.cast(Float),
        Property.details["deposit_full"].astext.cast(Float),
        Property.details["monthly_rent"].astext.cast(Float),
    )


def apply_filters(
    q,
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
):
    """فیلترهای مشترک بین فهرست فایل‌ها و خروجی PDF/اکسل، تا هردو دقیقاً یک منطق را دنبال کنند."""
    if city:
        q = q.filter(Property.city == city)
    if district:
        q = q.filter(Property.district.ilike(f"%{district}%"))
    if deal_type:
        q = q.filter(Property.deal_type == deal_type)
    if min_area is not None:
        q = q.filter(Property.area_m2 >= min_area)
    if max_area is not None:
        q = q.filter(Property.area_m2 <= max_area)
    if min_rooms is not None:
        q = q.filter(Property.rooms >= min_rooms)
    if has_elevator is not None:
        q = q.filter(Property.has_elevator == has_elevator)
    if has_parking is not None:
        q = q.filter(Property.has_parking == has_parking)
    if min_price is not None:
        q = q.filter(_price_expression() >= min_price)
    if max_price is not None:
        q = q.filter(_price_expression() <= max_price)
    return q


MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50


@router.get("/", response_model=PropertyListResponse)
def list_properties(
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
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    نکته‌ی مهم مقیاس: نسخه‌ی قبلی این endpoint یک `.limit(500)` هاردکد داشت که
    باعث می‌شد فایل‌های بعد از ۵۰۰ اُم بی‌صدا از دید مدیر پنهان بمانند. حالا
    صفحه‌بندی واقعی داریم: `total` تعداد واقعی نتایج مطابق فیلتر را برمی‌گرداند
    تا کلاینت بداند چند صفحه‌ی دیگر مانده، نه این‌که فرض کند همه چیز را دیده.
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    q = _base_query(db, current_user)
    q = apply_filters(
        q, city=city, district=district, deal_type=deal_type, min_area=min_area, max_area=max_area,
        min_rooms=min_rooms, has_elevator=has_elevator, has_parking=has_parking,
        min_price=min_price, max_price=max_price,
    )

    total = q.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    items = (
        q.order_by(Property.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PropertyListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/renewals", response_model=list[PropertyRead])
def upcoming_renewals(
    days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """قراردادهای اجاره/رهنی که ظرف `days` روز آینده پایان می‌یابند."""
    cutoff = date.today() + timedelta(days=days)
    q = _base_query(db, current_user).filter(
        Property.contract_end_date.isnot(None), Property.contract_end_date <= cutoff
    )
    return q.order_by(Property.contract_end_date.asc()).all()


@router.post("/", response_model=PropertyRead)
def create_property(
    data: PropertyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    prop = Property(**data.model_dump(), owner_agent_id=current_user.id)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.put("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    data: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = _base_query(db, current_user).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد یا دسترسی ندارید")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}")
def deactivate_property(
    property_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """حذف قطعی نداریم؛ فقط غیرفعال می‌شود تا سابقه از بین نرود."""
    prop = _base_query(db, current_user).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد یا دسترسی ندارید")
    prop.status = PropertyStatus.inactive
    db.commit()
    return {"ok": True}
