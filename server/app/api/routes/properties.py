from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form

from sqlalchemy.orm import Session
from sqlalchemy import func, Float, or_, and_, String, text
from app.db.session import get_db
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate, PropertyListResponse
from app.services.activity_log_service import log_activity
from app.models.property_image import PropertyImage
from app.models.property_favorite import PropertyFavorite
from datetime import date, timedelta, datetime, timezone
from app.api.deps import get_current_user, require_admin   
from app.models.notification import Notification         


router = APIRouter(prefix="/properties", tags=["properties"])

def _money_fa(n) -> str:
    try:
        return f"{int(float(n)):,}"
    except (TypeError, ValueError):
        return "0"


def _price_display(deal_type: str, details: dict) -> Optional[str]:
    """قیمت نمایشی بسته به نوع معامله — برای ستون «قیمت» جدول و بج کارت."""
    d = details or {}
    if deal_type == "sale":
        return f"{_money_fa(d.get('price'))} تومان" if d.get("price") else None
    if deal_type == "rent":
        parts = []
        if d.get("deposit"):
            parts.append(f"ودیعه {_money_fa(d['deposit'])}")
        if d.get("monthly_rent"):
            parts.append(f"اجاره {_money_fa(d['monthly_rent'])}")
        return " / ".join(parts) if parts else None
    if deal_type == "mortgage":
        return f"رهن {_money_fa(d.get('deposit_full'))}" if d.get("deposit_full") else None
    if deal_type == "presale":
        return f"پیش‌فروش {_money_fa(d.get('total_price'))}" if d.get("total_price") else None
    return None


def _price_per_m2_display(deal_type: str, details: dict, area) -> Optional[str]:
    if deal_type != "sale" or not area:
        return None
    price = (details or {}).get("price")
    if not price:
        return None
    return f"{_money_fa(round(float(price) / float(area)))} تومان"


def _base_query(db: Session, current_user: User, status: PropertyStatus = PropertyStatus.active):
    q = db.query(Property).filter(Property.status == status)
    q = q.filter(Property.deleted_at.is_(None))
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


def _attach_cover_info(db: Session, response: PropertyListResponse,
                       current_user: User = None) -> PropertyListResponse:
    ids = [it.id for it in response.items]
    if not ids:
        return response
    rows = (
        db.query(PropertyImage.property_id, func.min(PropertyImage.id))
        .filter(PropertyImage.property_id.in_(ids))
        .group_by(PropertyImage.property_id)
        .all()
    )
    cover_map = dict(rows)
    fav_ids = set()
    if current_user is not None:
        try:
            fav_ids = set(
                f.property_id for f in db.query(PropertyFavorite)
                .filter(PropertyFavorite.user_id == current_user.id,
                        PropertyFavorite.property_id.in_(ids)).all()
            )
        except Exception:
            # جدول ستاره‌ها هنوز ساخته نشده (migration عقب افتاده) —
            # فهرست فایل‌ها نباید به‌خاطر یک فیچر فرعی ۵۰۰ بدهد
            fav_ids = set()
    for it in response.items:
        cid = cover_map.get(it.id)
        it.cover_image_id = cid
        it.has_images = cid is not None
        dt = it.deal_type.value if hasattr(it.deal_type, "value") else str(it.deal_type)
        it.price_display = _price_display(dt, it.details)
        it.price_per_m2_display = _price_per_m2_display(dt, it.details, it.area_m2)
        it.is_favorite = it.id in fav_ids
    return response

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
    property_type: Optional[str] = None
):
    """فیلترهای مشترک بین فهرست فایل‌ها و خروجی PDF/اکسل، تا هردو دقیقاً یک منطق را دنبال کنند."""

    if property_type:
        q = q.filter(
            func.json_typeof(Property.property_types) == 'array',
            func.json_array_length(Property.property_types) >= 0,
        )
        # جست‌وجوی مقدار در آرایه‌ی JSON:
        q = q.filter(
            Property.property_types.cast(String).like(f'%"{property_type}"%')
        )

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
    property_type: Optional[str] = None,
    urgent_only: Optional[bool] = None,
    favorites_only: Optional[bool] = None,
    min_build_year: Optional[int] = None,
    max_build_year: Optional[int] = None,
    max_total_units: Optional[int] = None,
    min_total_units: Optional[int] = None,
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
        min_price=min_price, max_price=max_price, search=search, property_type=property_type,
    )
    if urgent_only:
        today = date.today()
        week_later = today + timedelta(days=7)
        q = q.filter(or_(
            and_(Property.urgent_until.isnot(None), Property.urgent_until >= today),
            and_(Property.contract_end_date.isnot(None),
                 Property.contract_end_date >= today,
                 Property.contract_end_date <= week_later),
        ))
    if favorites_only:
        q = q.join(PropertyFavorite, PropertyFavorite.property_id == Property.id).filter(
            PropertyFavorite.user_id == current_user.id)
    order_clause = _build_order_clause(sort_by, sort_order)

    if min_build_year is not None:
        q = q.filter(Property.build_year >= min_build_year)
    if max_build_year is not None:
        q = q.filter(Property.build_year <= max_build_year)
    if max_total_units is not None:
        q = q.filter(Property.total_units <= max_total_units)

    if min_total_units is not None:
        q = q.filter(Property.total_units >= min_total_units)
    return _attach_cover_info(db, _paginate(q, page, page_size, order_clause=order_clause),
                              current_user=current_user)


@router.get("/archived", response_model=PropertyListResponse)
def list_archived_properties(
    status: str = "inactive",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    st = {"sold": PropertyStatus.sold, "rented": PropertyStatus.rented}.get(status, PropertyStatus.inactive)
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
        .filter(Property.status == PropertyStatus.active, or_(*conds), Property.deleted_at.is_(None))
        
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

@router.post("/scan-expiration")
def scan_expiration(days: int = 90, db: Session = Depends(get_db),
                    _admin: User = Depends(require_admin)):
    """
    مدیر فایل‌های فعال قدیمی را اسکن می‌کند؛ به مالک هرکدام اطلاع‌یه می‌رود
    تا خودش تصمیم بگیرد: انقضا (به بایگانی) یا نگه‌داشتن (بازبینی بعدی).
    """
    cutoff = date.today() - timedelta(days=days)
    today = date.today()
    candidates = []
    for p in db.query(Property).filter(Property.status == PropertyStatus.active).all():
        never_reviewed = p.expire_review_at is None and p.expire_notified_at is None \
            and p.created_at is not None and p.created_at.date() <= cutoff
        review_due = p.expire_review_at is not None and p.expire_review_at <= today
        if never_reviewed or review_due:
            candidates.append(p)

    now_utc = datetime.now(timezone.utc)
    for p in candidates:
        db.add(Notification(
            user_id=p.owner_agent_id,
            title="⏳ فایل قدیمی — تکلیف انقضا",
            body=f"فایل #{p.id} ({p.city} — {p.address or ''}) بیش از {days} روز فعال مانده. "
                 f"در زنگ اطلاع‌یه، تکلیفش را مشخص کنید (انقضا یا نگه‌داشتن).",
            entity_type="expiration", entity_id=p.id,
        ))
        p.expire_notified_at = now_utc
    db.commit()
    return {"notified": len(candidates)}


def _expire_access(db: Session, property_id: int, current_user: User) -> Property:
    p = db.get(Property, property_id)
    if not p:
        raise HTTPException(404, "فایل پیدا نشد")
    if current_user.role != UserRole.admin and p.owner_agent_id != current_user.id:
        raise HTTPException(403, "فقط مالک فایل یا مدیر مجاز است")
    return p


@router.post("/{property_id}/expire-confirm")
def expire_confirm(property_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """تأیید انقضا توسط مالک فایل → به بایگانی (غیرفعال) می‌رود."""
    p = _expire_access(db, property_id, current_user)
    p.status = PropertyStatus.inactive
    db.commit()
    log_activity(db, current_user.id, "deactivate", "property", p.id, detail=f"انقضای خودکار — {p.city}")
    return {"ok": True}


@router.post("/{property_id}/expire-keep")
def expire_keep(property_id: int, days: int = 90, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """نگه‌داشتن فایل → بعد از `days` روز دیگر همان سؤال پرسیده می‌شود."""
    p = _expire_access(db, property_id, current_user)
    p.expire_review_at = date.today() + timedelta(days=days)
    db.commit()
    return {"ok": True}


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

@router.get("/stale", response_model=list[PropertyRead])
def stale_properties(days: int = 30, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """فایل‌های فعالِ بدون هیچ پیگیریِ وصل‌شده و قدیمی‌تر از N روز — لیست کار روزانه."""
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
    q = _base_query(db, current_user, status=PropertyStatus.active).filter(
        Property.created_at <= cutoff_dt)
    try:
        rows = db.execute(text(
            "SELECT DISTINCT property_id FROM follow_ups WHERE property_id IS NOT NULL")).all()
        followed = [r[0] for r in rows]
    except Exception:
        followed = []
    if followed:
        q = q.filter(~Property.id.in_(followed))
    return q.order_by(Property.created_at.asc()).limit(100).all()


@router.post("/{property_id}/favorite")
def toggle_favorite(property_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """ستارهٔ شخصی: اگر هست برمی‌دارد، نیست اضافه می‌کند. هر کاربر لیست خودش."""
    prop = _base_query(db, current_user).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "فایل پیدا نشد یا دسترسی ندارید")
    existing = db.query(PropertyFavorite).filter(
        PropertyFavorite.user_id == current_user.id,
        PropertyFavorite.property_id == property_id,
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"is_favorite": False}
    db.add(PropertyFavorite(user_id=current_user.id, property_id=property_id))
    db.commit()
    return {"is_favorite": True}


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


@router.post("/notify-matches/{property_id}")
def notify_matching_requests(property_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """بعد از ثبت فایل جدید: درخواست‌های بازِ منطبق را پیدا کن و به مالک هر درخواست اطلاع‌یه بزن."""
    from app.api.routes.client_requests import ClientRequest, RequestStatus, _matching_properties
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "فایل پیدا نشد")
    if current_user.role != UserRole.admin and prop.owner_agent_id != current_user.id:
        raise HTTPException(403, "دسترسی ندارید")

    open_reqs = db.query(ClientRequest).filter(ClientRequest.status == RequestStatus.open).all()
    notified = 0
    for req in open_reqs:
        owner = db.get(User, req.owner_agent_id)
        if not owner or not owner.is_active:
            continue
        # دسترسی: مالک درخواست باید بتواند این فایل را ببیند (مشاور: فقط فایل‌های خودش؛ مدیر: همه)
        if owner.role != UserRole.admin and prop.owner_agent_id != owner.id:
            continue
        matches = _matching_properties(db, owner, req).filter(Property.id == property_id).first()
        if matches:
            db.add(Notification(
                user_id=req.owner_agent_id,
                title="🎯 فایل منطبق جدید برای درخواست مشتری",
                body=(f"فایل #{prop.id} ({prop.city} — {prop.address or ''}) با درخواست "
                      f"«{req.customer_name}» تطبیق دارد. در تب «درخواست مشتری‌ها» ← «فایل‌های منطبق» ببینش."),
                entity_type="client_request", entity_id=req.id,
            ))
            notified += 1
    db.commit()
    return {"notified": notified}

@router.post("/flag-shared/{property_id}")
def flag_shared_listing(property_id: int, other_property_id: int = Form(...),
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """مشاور دوم فایل مشابه را با تأیید ثبت کرد → به مدیر اطلاع‌یه بده که این آگهی/فایل
    توسط دو نفر (مالک مشترک) ثبت شده است."""
    from app.models.notification import Notification as N
    prop = db.get(Property, property_id)
    other = db.get(Property, other_property_id)
    if not prop or not other:
        raise HTTPException(404, "فایل پیدا نشد")
    if current_user.role != UserRole.admin and (prop.owner_agent_id != current_user.id or other.owner_agent_id != current_user.id):
        raise HTTPException(403, "دسترسی ندارید")
    admins = db.query(User).filter(User.role == UserRole.admin).all()
    for a in admins:
        db.add(N(user_id=a.id, title="🤝 فایل مشابه توسط دو مشاور ثبت شد",
                 body=(f"فایل #{prop.id} ({prop.city} — {prop.address or ''}) توسط {current_user.full_name} ثبت شد؛ "
                       f"فایل مشابه #{other.id} قبلاً ثبت بوده. تصمیم: نگه‌داشتن هر دو / ادغام، با تو."),
                 entity_type="property", entity_id=prop.id))
    db.commit()
    return {"ok": True}

    
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


@router.post("/{property_id}/soft-delete")
def soft_delete_property(property_id: int, db: Session = Depends(get_db),
                         admin: User = Depends(require_admin)):
    """حذف نرم — فقط مدیر. رکورد می‌ماند ولی از همهٔ لیست‌ها/جست‌وجوها مخفی می‌شود."""
    prop = _base_query(db, admin).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "فایل پیدا نشد یا دسترسی ندارید")
    prop.deleted_at = datetime.now(timezone.utc)
    db.commit()
    log_activity(db, admin.id, "deactivate", "property", prop.id,
                 detail=f"حذف نرم — {prop.city} — {prop.address or ''}")
    return {"ok": True}
