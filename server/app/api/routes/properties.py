from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, Float, or_, and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate, PropertyListResponse
from app.services.activity_log_service import log_activity

router = APIRouter(prefix="/properties", tags=["properties"])


def _base_query(db: Session, current_user: User, status: PropertyStatus = PropertyStatus.active):
    q = db.query(Property).filter(Property.status == status)
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
    search: Optional[str] = None,
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
    if search:
        # جستجوی آزاد هم‌زمان روی چند ستون — کاربر فقط تایپ می‌کند، نیازی به
        # دانستن این‌که کلمه در کدام فیلد است ندارد.
        pattern = f"%{search}%"
        q = q.filter(or_(
            Property.city.ilike(pattern),
            Property.district.ilike(pattern),
            Property.address.ilike(pattern),
            Property.notes.ilike(pattern),
            Property.owner_name.ilike(pattern),
            Property.owner_phone.ilike(pattern),
        ))
    return q


MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50

SORTABLE_FIELDS = {
    "created_at": Property.created_at,
    "area_m2": Property.area_m2,
    "price": _price_expression(),
    "contract_end_date": Property.contract_end_date,
}


def _build_order_clause(sort_by: Optional[str], sort_order: Optional[str]):
    column = SORTABLE_FIELDS.get(sort_by, Property.created_at)
    return column.asc() if sort_order == "asc" else column.desc()


def _paginate(q, page: int, page_size: int, order_clause=None) -> PropertyListResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    total = q.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    if order_clause is None:
        order_clause = Property.created_at.desc()

    items = (
        q.order_by(order_clause)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PropertyListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


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
    search: Optional[str] = None,
    owner_agent_id: Optional[int] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
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

    `sort_by` یکی از: created_at, area_m2, price, contract_end_date
    `sort_order` یکی از: asc, desc
    """
    q = _base_query(db, current_user, status=PropertyStatus.active)
    if current_user.role == UserRole.admin and owner_agent_id:
        q = q.filter(Property.owner_agent_id == owner_agent_id)
    q = apply_filters(
        q, city=city, district=district, deal_type=deal_type, min_area=min_area, max_area=max_area,
        min_rooms=min_rooms, has_elevator=has_elevator, has_parking=has_parking,
        min_price=min_price, max_price=max_price, search=search,
    )
    order_clause = _build_order_clause(sort_by, sort_order)
    return _paginate(q, page, page_size, order_clause=order_clause)


@router.get("/archived", response_model=PropertyListResponse)
def list_archived_properties(
    status: str = "inactive",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if status not in ("inactive", "sold"):
        raise HTTPException(status_code=400, detail="status باید inactive یا sold باشد")
    st = PropertyStatus.sold if status == "sold" else PropertyStatus.inactive
    q = _base_query(db, current_user, status=st)
    return _paginate(q, page, page_size)


def _norm_text(s: str | None) -> str:
    return " ".join((s or "").strip().lower().split())


@router.get("/check-duplicate")
def check_duplicate(
    owner_phone: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    هشدار فایل مشابه (مسدودکننده نیست): بر اساس تلفن مالک یا شهر+آدرس یکسان.
    عمداً بین همه‌ی مشاورها جست‌وجو می‌کند تا ثبت فایل تکراری توسط دو نفر متوجه شود.
    """
    phone = (owner_phone or "").strip()
    ncity, naddr = _norm_text(city), _norm_text(address)

    conds = []
    if phone:
        conds.append(Property.owner_phone == phone)
    if ncity and naddr:
        conds.append(and_(
            func.lower(Property.city) == ncity,
            func.lower(func.trim(Property.address)) == naddr,
        ))
    if not conds:
        return []

    rows = (
        db.query(Property, User.full_name)
        .join(User, Property.owner_agent_id == User.id)
        .filter(Property.status == PropertyStatus.active, or_(*conds))
        .order_by(Property.created_at.desc())
        .limit(10)
        .all()
    )
    return [{
        "id": p.id,
        "city": p.city,
        "address": p.address,
        "deal_type": p.deal_type.value if hasattr(p.deal_type, "value") else str(p.deal_type),
        "owner_name": p.owner_name,
        "owner_phone": p.owner_phone,
        "agent_name": agent_name,
        "match_kind": "exact" if (ncity and naddr and _norm_text(p.city) == ncity
                                  and _norm_text(p.address) == naddr) else "phone",
    } for p, agent_name in rows]


@router.post("/{property_id}/reactivate", response_model=PropertyRead)
def reactivate_property(
    property_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """یک فایل غیرفعال‌شده را دوباره فعال می‌کند (بازگرداندن از آرشیو)."""
    q = db.query(Property).filter(Property.id == property_id, Property.status != PropertyStatus.active)
    if current_user.role != UserRole.admin:
        q = q.filter(Property.owner_agent_id == current_user.id)
    prop = q.first()
    if not prop:
        raise HTTPException(status_code=404, detail="فایل غیرفعال‌شده‌ای با این مشخصات پیدا نشد")
    prop.status = PropertyStatus.active
    db.commit()
    db.refresh(prop)
    log_activity(db, current_user.id, "reactivate", "property", prop.id, detail=f"{prop.city} — {prop.address or ''}")
    return prop


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
    log_activity(db, current_user.id, "create", "property", prop.id, detail=f"{prop.city} — {prop.address or ''}")
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

    # --- قفل هم‌زمان (Optimistic Locking) ---
    # اگر نسخه‌ای که کلاینت خوانده با نسخه‌ی فعلی دیتابیس فرق دارد، یعنی شخص
    # دیگری (یا خودِ همین کاربر از یک تب دیگر) بین‌این‌حین این فایل را تغییر
    # داده. به‌جای رونویسی بی‌صدا، خطای ۴۰۹ برمی‌گردانیم تا کلاینت فایل را
    # دوباره بارگذاری کند.
    if data.version != prop.version:
        raise HTTPException(
            status_code=409,
            detail="این فایل توسط شخص دیگری تغییر کرده است. لطفاً فایل را دوباره باز کنید و تغییرات را مجدد اعمال کنید.",
        )

    update_fields = data.model_dump(exclude_unset=True, exclude={"version"})
    for field, value in update_fields.items():
        setattr(prop, field, value)
    prop.version += 1
    db.commit()
    db.refresh(prop)
    log_activity(db, current_user.id, "update", "property", prop.id, detail=f"{prop.city} — {prop.address or ''}")
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
    log_activity(db, current_user.id, "deactivate", "property", prop.id, detail=f"{prop.city} — {prop.address or ''}")
    return {"ok": True}
