import io
import os
import shutil
import uuid
from datetime import date, datetime, timezone
from app.models.notification import Notification
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.deal import Deal, DealStatus, CommissionPayment
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.deal import DealCreate, DealUpdate, PaymentRead, BalanceRead
from app.services.activity_log_service import log_activity
from app.services.deal_pdf import build_deal_settlement_pdf, build_balances_pdf

router = APIRouter(prefix="/deals", tags=["deals"])
RECEIPT_DIR = os.path.join("media", "receipts")


def _deal_out(db: Session, d: Deal) -> dict:
    to_agent = db.query(func.coalesce(func.sum(CommissionPayment.amount), 0)).filter(
        CommissionPayment.deal_id == d.id, CommissionPayment.kind == "to_agent").scalar()
    from_agent = db.query(func.coalesce(func.sum(CommissionPayment.amount), 0)).filter(
        CommissionPayment.deal_id == d.id, CommissionPayment.kind == "from_agent").scalar()
    return {
        "id": d.id, "property_id": d.property_id, "agent_id": d.agent_id,
        "deal_amount": d.deal_amount, "commission_percent": d.commission_percent,
        "commission_amount": d.commission_amount, "status": d.status,
        "contract_date": d.contract_date, "finalized_at": d.finalized_at,
        "notes": d.notes, "created_at": d.created_at,
        # "paid_total": int(paid), "remaining": max(int(d.commission_amount) - int(paid), 0),
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
        commission_amount=int(round(data.deal_amount * pct / 100)),
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
        d.commission_amount = int(round(d.deal_amount * d.commission_percent / 100))
    db.commit()
    db.refresh(d)
    return _deal_out(db, d)


@router.post("/{deal_id}/finalize")
def finalize_deal(deal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """معامله قطعی می‌شود + فایل ملکی به بایگانی (sold) می‌رود."""
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
    log_activity(db, admin.id, "finalize", "deal", d.id, detail=f"قطعی — پورسانت {d.commission_amount:,}")
    db.add(Notification(user_id=d.agent_id, title="معامله‌ی شما قطعی شد",
                        body=f"معامله #{d.id} قطعی شد — پورسانت {d.commission_amount:,} تومان.",
                        entity_type="deal", entity_id=d.id))
    db.commit()
    return _deal_out(db, d)



@router.post("/{deal_id}/unfinalize")
def unfinalize_deal(deal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """بازگرداندن معامله‌ی قطعی‌شده به «در جریان» (برای اصلاح مبلغ یا لغو)."""
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
    return [PaymentRead(id=p.id, amount=p.amount, paid_date=p.paid_date,
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
        os.remove(p.receipt_path)  # رسید قبلی جایگزین می‌شود
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
    log_activity(db, admin.id, "create", "deal_payment", deal_id, detail=f"پرداخت {amount:,} تومان")
    db.add(Notification(user_id=d.agent_id, title="پرداخت پورسانت ثبت شد",
                        body=f"برای معامله #{deal_id} پرداخت {amount:,} تومانی ثبت شد.",
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
def payment_receipt(payment_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    p = db.get(CommissionPayment, payment_id)
    if not p or not p.receipt_path or not os.path.exists(p.receipt_path):
        raise HTTPException(404, "رسیدی ثبت نشده است")
    return FileResponse(p.receipt_path)


def _balances(db: Session) -> list[dict]:
    agents = db.query(User).all()      
    # agents = db.query(User).filter(User.role == UserRole.agent).all()
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