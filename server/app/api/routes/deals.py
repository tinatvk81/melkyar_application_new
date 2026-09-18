import io
import os
import shutil
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.notification import Notification
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin, get_current_user
from app.db.session import get_db
from app.models.deal import Deal, DealStatus, CommissionPayment
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.deal import DealCreate, DealUpdate, PaymentRead, BalanceRead
from app.services.activity_log_service import log_activity
from app.services.deal_pdf import build_deal_settlement_pdf, build_balances_pdf

router = APIRouter(prefix="/deals", tags=["deals"])
RECEIPT_DIR = os.path.join("media", "receipts")


def _commission_of(amount: int, percent: float) -> int:
    """محاسبه‌ی دقیق پورسانت با Decimal — مبالغ خیلی بزرگ نباید از float رد شوند."""
    return int(round(Decimal(amount) * Decimal(str(percent)) / Decimal(100)))


def _deal_out(db: Session, d: Deal) -> dict:
    to_agent = db.query(func.coalesce(func.sum(CommissionPayment.amount), 0)).filter(
        CommissionPayment.deal_id == d.id, CommissionPayment.kind == "to_agent").scalar()
    from_agent = db.query(func.coalesce(func.sum(CommissionPayment.amount), 0)).filter(
        CommissionPayment.deal_id == d.id, CommissionPayment.kind == "from_agent").scalar()
    return {
        "id": d.id, "property_id": d.property_id, "agent_id": d.agent_id,
        "deal_amount": int(d.deal_amount),
        "commission_percent": float(d.commission_percent),
        "commission_amount": int(d.commission_amount),
        "status": d.status,
        "contract_date": d.contract_date, "finalized_at": d.finalized_at,
        "notes": d.notes, "created_at": d.created_at,
        "paid_total": int(to_agent),
        "received_total": int(from_agent),
        "remaining": int(d.commission_amount) - int(to_agent) + int(from_agent),
    }


@router.get("/")
def list_deals(agent_id: int | None = None, status: str | None = None,
               db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    q = db.query(Deal)
    if agent_id:
        q = q.filter(Deal.agent_id == agent_id)
    if status:
        q = q.filter(Deal.status == DealStatus(status))
    return [_deal_out(db, d) for d in q.order_by(Deal.created_at.desc()).all()]


@router.post("/")
def create_deal(data: DealCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    prop = db.get(Property, data.property_id)
    if not prop:
        raise HTTPException(404, "فایل ملکی پیدا نشد")
    agent = db.get(User, data.agent_id)
    if not agent:
        raise HTTPException(404, "مشاور پیدا نشد")

    pct = data.commission_percent
    if pct is None:
        rates = agent.commission_rates or {}
        key = prop.deal_type.value if hasattr(prop.deal_type, "value") else str(prop.deal_type)
        if key not in rates:
            raise HTTPException(400, f"درصد پورسانت این مشاور برای نوع «{key}» تنظیم نشده است. ابتدا در مدیریت کاربران درصد را وارد کنید.")
        pct = float(rates[key])

    deal = Deal(
        property_id=data.property_id, agent_id=data.agent_id,
        deal_amount=data.deal_amount, commission_percent=pct,
        commission_amount=_commission_of(data.deal_amount, pct),
        contract_date=data.contract_date, notes=data.notes,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    log_activity(db, admin.id, "create", "deal", deal.id, detail=f"معامله {data.deal_amount:,} تومان")
    return _deal_out(db, deal)


@router.put("/{deal_id}")
def update_deal(deal_id: int, data: DealUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    changes = data.model_dump(exclude_unset=True)
    for f, v in changes.items():
        setattr(d, f, v)
    if "deal_amount" in changes or "commission_percent" in changes:
        d.commission_amount = _commission_of(d.deal_amount, d.commission_percent)
    db.commit()
    db.refresh(d)
    return _deal_out(db, d)


@router.post("/{deal_id}/finalize")
def finalize_deal(deal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    if d.status == DealStatus.finalized:
        raise HTTPException(400, "این معامله قبلاً قطعی شده است — نیازی به قطعی دوباره نیست")
    if d.status == DealStatus.canceled:
        raise HTTPException(400, "این معامله لغو شده و قابل قطعی‌کردن نیست")

    d.status = DealStatus.finalized
    d.finalized_at = datetime.now(timezone.utc)
    prop = db.get(Property, d.property_id)
    if prop:
        prop.status = PropertyStatus.sold
    db.commit()
    db.refresh(d)
    log_activity(db, admin.id, "finalize", "deal", d.id, detail=f"قطعی — پورسانت {int(d.commission_amount):,}")
    db.add(Notification(user_id=d.agent_id, title="معامله‌ی شما قطعی شد",
                        body=f"معامله #{d.id} قطعی شد — پورسانت {int(d.commission_amount):,} تومان.",
                        entity_type="deal", entity_id=d.id))
    db.commit()
    return _deal_out(db, d)


@router.post("/{deal_id}/unfinalize")
def unfinalize_deal(deal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    if d.status != DealStatus.finalized:
        raise HTTPException(400, "فقط معامله‌ی قطعی‌شده قابل بازگشت است")
    d.status = DealStatus.pending
    d.finalized_at = None
    prop = db.get(Property, d.property_id)
    if prop and prop.status == PropertyStatus.sold:
        prop.status = PropertyStatus.active
    db.commit()
    db.refresh(d)
    log_activity(db, admin.id, "update", "deal", d.id, detail="بازگشت از قطعی به در جریان")
    db.add(Notification(user_id=d.agent_id, title="معامله به «در جریان» برگشت",
                        body=f"معامله #{d.id} از حالت قطعی خارج شد.", entity_type="deal", entity_id=d.id))
    db.commit()
    return _deal_out(db, d)


@router.post("/{deal_id}/cancel")
def cancel_deal(deal_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    if d.status == DealStatus.finalized:
        raise HTTPException(400, "معامله‌ی قطعی‌شده قابل لغو نیست — برای جبران، «دریافت از مشاور» ثبت کنید")
    if d.status == DealStatus.canceled:
        raise HTTPException(400, "این معامله از قبل لغو شده است")

    d.status = DealStatus.canceled
    db.commit()
    return _deal_out(db, d)


@router.get("/{deal_id}/payments", response_model=list[PaymentRead])
def list_payments(deal_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    rows = db.query(CommissionPayment).filter(CommissionPayment.deal_id == deal_id).order_by(CommissionPayment.id).all()
    return [PaymentRead(id=p.id, amount=int(p.amount), paid_date=p.paid_date,
                        note=p.note, has_receipt=bool(p.receipt_path),
                        kind=p.kind) for p in rows]


@router.post("/payments/{payment_id}/receipt")
def attach_receipt(payment_id: int, receipt: UploadFile = File(...),
                   db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    p = db.get(CommissionPayment, payment_id)
    if not p:
        raise HTTPException(404, "پرداخت پیدا نشد")
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    ext = os.path.splitext(receipt.filename)[1] or ".jpg"
    if p.receipt_path and os.path.exists(p.receipt_path):
        os.remove(p.receipt_path)
    p.receipt_path = os.path.join(RECEIPT_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(p.receipt_path, "wb") as f:
        shutil.copyfileobj(receipt.file, f)
    db.commit()
    log_activity(db, admin.id, "update", "deal_payment", p.deal_id, detail="رسید پرداخت ثبت/تعویض شد")
    return {"ok": True}


@router.post("/{deal_id}/payments")
def add_payment(deal_id: int, amount: int = Form(...), paid_date: str | None = Form(None),
                note: str | None = Form(None), kind: str = Form("to_agent"),
                receipt: UploadFile | None = File(None), db=Depends(get_db), admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    pdate = date.fromisoformat(paid_date) if paid_date else None
    receipt_path = None
    if receipt and receipt.filename:
        os.makedirs(RECEIPT_DIR, exist_ok=True)
        ext = os.path.splitext(receipt.filename)[1] or ".jpg"
        receipt_path = os.path.join(RECEIPT_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(receipt_path, "wb") as f:
            shutil.copyfileobj(receipt.file, f)

    if kind not in ("to_agent", "from_agent"):
        raise HTTPException(400, "kind نامعتبر است")

    p = CommissionPayment(deal_id=deal_id, amount=amount, paid_date=pdate, note=note,
                          receipt_path=receipt_path, kind=kind)
    db.add(p)
    db.commit()
    db.refresh(p)
    log_activity(db, admin.id, "create", "deal_payment", deal_id, detail=f"پرداخت {int(amount):,} تومان")
    db.add(Notification(user_id=d.agent_id, title="پرداخت پورسانت ثبت شد",
                        body=f"برای معامله #{deal_id} پرداخت {int(amount):,} تومانی ثبت شد.",
                        entity_type="deal", entity_id=deal_id))
    db.commit()
    return {"ok": True, "payment_id": p.id}


@router.delete("/payments/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(CommissionPayment, payment_id)
    if not p:
        raise HTTPException(404, "پرداخت پیدا نشد")
    if p.receipt_path and os.path.exists(p.receipt_path):
        os.remove(p.receipt_path)
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.get("/payments/{payment_id}/receipt")
def payment_receipt(payment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """مدیر به همه رسیدها دسترسی دارد؛ مشاور فقط به رسیدهای معامله‌های خودش."""
    p = db.get(CommissionPayment, payment_id)
    if not p or not p.receipt_path or not os.path.exists(p.receipt_path):
        raise HTTPException(404, "رسیدی ثبت نشده است")
    deal = db.get(Deal, p.deal_id)
    if user.role != UserRole.admin and (deal is None or deal.agent_id != user.id):
        raise HTTPException(403, "به رسید این پرداخت دسترسی ندارید")
    return FileResponse(p.receipt_path)


# ---------------------------------------------------------------- دفتر حساب
def _ledger(db: Session, user: User) -> dict:
    """دفتر کامل یک کاربر: همهٔ معامله‌هایش (هر وضعیتی) + پرداخت‌های هر معامله + جمع‌ها."""
    deals = db.query(Deal).filter(Deal.agent_id == user.id).order_by(Deal.created_at.desc()).all()
    items = []
    earned = 0
    paid_net = 0
    for d in deals:
        pays = db.query(CommissionPayment).filter(CommissionPayment.deal_id == d.id).order_by(CommissionPayment.id).all()
        to_sum = int(sum(p.amount for p in pays if p.kind == "to_agent"))
        from_sum = int(sum(p.amount for p in pays if p.kind == "from_agent"))
        if d.status == DealStatus.finalized:
            earned += int(d.commission_amount)
        paid_net += to_sum - from_sum
        items.append({
            "id": d.id, "property_id": d.property_id,
            "deal_amount": int(d.deal_amount),
            "commission_percent": float(d.commission_percent),
            "commission_amount": int(d.commission_amount),
            "status": d.status,
            "contract_date": d.contract_date,
            "paid_total": to_sum, "received_total": from_sum,
            "remaining": int(d.commission_amount) - to_sum + from_sum,
            "payments": [{
                "id": p.id, "amount": int(p.amount), "paid_date": p.paid_date,
                "note": p.note, "kind": p.kind, "has_receipt": bool(p.receipt_path),
            } for p in pays],
        })
    return {
        "user_id": user.id, "full_name": user.full_name,
        "deals_count": len(items),
        "finalized_count": sum(1 for d in deals if d.status == DealStatus.finalized),
        "earned": earned, "paid_total": paid_net,
        "remaining": earned - paid_net,
        "deals": items,
    }


@router.get("/my-ledger")
def my_ledger(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """دفتر کاربر لاگین‌شده (مشاور فقط خودش را می‌بیند — بر اساس توکن)."""
    return _ledger(db, user)


@router.get("/ledger/{user_id}")
def user_ledger(user_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """دفتر هر کاربر — فقط مدیر."""
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "کاربر پیدا نشد")
    return _ledger(db, u)


@router.get("/my-ledger/pdf")
def my_ledger_pdf(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.ledger_pdf import build_agent_ledger_pdf
    pdf = build_agent_ledger_pdf(_ledger(db, user))
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=my-ledger.pdf"})


@router.get("/ledger/{user_id}/pdf")
def user_ledger_pdf(user_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.services.ledger_pdf import build_agent_ledger_pdf
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "کاربر پیدا نشد")
    pdf = build_agent_ledger_pdf(_ledger(db, u))
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename=ledger-{user_id}.pdf"})


@router.get("/ledger-all/pdf")
def all_ledgers_pdf(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """دفتر همهٔ کاربران در یک PDF — فقط مدیر."""
    from app.services.ledger_pdf import build_all_ledgers_pdf
    users = db.query(User).order_by(User.id).all()
    pdf = build_all_ledgers_pdf([_ledger(db, u) for u in users])
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=all-ledgers.pdf"})


# ---------------------------------------------------------------- مانده‌ها
def _balances(db: Session) -> list[dict]:
    users = db.query(User).all()
    agents = db.query(User).all()
    earned = dict(db.query(Deal.agent_id, func.coalesce(func.sum(Deal.commission_amount), 0))
                  .filter(Deal.status == DealStatus.finalized).group_by(Deal.agent_id).all())
    to_map = dict(db.query(Deal.agent_id, func.coalesce(func.sum(CommissionPayment.amount), 0))
                  .join(CommissionPayment, CommissionPayment.deal_id == Deal.id)
                  .filter(CommissionPayment.kind == "to_agent").group_by(Deal.agent_id).all())
    from_map = dict(db.query(Deal.agent_id, func.coalesce(func.sum(CommissionPayment.amount), 0))
                    .join(CommissionPayment, CommissionPayment.deal_id == Deal.id)
                    .filter(CommissionPayment.kind == "from_agent").group_by(Deal.agent_id).all())
    return [{
        "user_id": u.id, "full_name": u.full_name, "username": u.username,
        "commission_rates": u.commission_rates or {},
        "earned": int(earned.get(u.id, 0)),
        "paid": int(to_map.get(u.id, 0)) - int(from_map.get(u.id, 0)),
        "remaining": int(earned.get(u.id, 0)) - (int(to_map.get(u.id, 0)) - int(from_map.get(u.id, 0))),
        "is_active": u.is_active,
    } for u in agents]


@router.get("/balances", response_model=list[BalanceRead])
def balances(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return _balances(db)


@router.get("/balances/pdf")
def balances_pdf(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    pdf = build_balances_pdf(_balances(db))
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=agent-balances.pdf"})


@router.get("/{deal_id}/settlement-pdf")
def settlement_pdf(deal_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    payments = [{"amount": p.amount, "paid_date": p.paid_date, "note": p.note}
                for p in db.query(CommissionPayment).filter(CommissionPayment.deal_id == deal_id).all()]
    agent = db.get(User, d.agent_id)
    pdf = build_deal_settlement_pdf(_deal_out(db, d), agent.full_name if agent else "", payments)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=settlement.pdf"})


from app.services.contract_pdf import build_contract_pdf

@router.get("/{deal_id}/contract-pdf")
def contract_pdf(deal_id: int, agency_name: str = "آژانس املاک",
                 db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    d = db.get(Deal, deal_id)
    if not d:
        raise HTTPException(404, "معامله پیدا نشد")
    payments = [{"amount": p.amount, "paid_date": p.paid_date, "note": p.note}
                for p in db.query(CommissionPayment).filter(CommissionPayment.deal_id == deal_id).all()]
    agent = db.get(User, d.agent_id)
    pdf = build_contract_pdf(_deal_out(db, d), agent.full_name if agent else "", payments, agency_name)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=contract.pdf"})