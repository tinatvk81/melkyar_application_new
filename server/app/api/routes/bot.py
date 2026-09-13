from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.bot_faq import BotFaq
from app.models.user import User

router = APIRouter(prefix="/bot", tags=["chatbot"])


class AskIn(BaseModel):
    text: str


@router.post("/ask")
def ask(data: AskIn, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """پاسخ خودکار به سؤال بر اساس سؤالات متداول ثبت‌شده."""
    q = data.text.strip()
    if not q:
        raise HTTPException(400, "متن سؤال خالی است")

    faqs = db.query(BotFaq).all()
    if not faqs:
        return {"answer": "فعلاً سؤالات متداولی ثبت نشده است. با مدیر تماس بگیرید.", "matched": None}

    q_words = set(q.lower().replace("؟", " ").replace("?", " ").split())
    best, best_score = None, 0
    for f in faqs:
        f_words = set(f.question.lower().replace("؟", " ").replace("?", " ").split())
        score = len(q_words & f_words)
        if score > best_score:
            best, best_score = f, score

    if best and best_score >= 1:
        return {"answer": best.answer, "matched": best.question}
    return {"answer": "سؤال شما را کامل متوجه نشدم. عبارت دقیق‌تری بنویسید یا با مدیر تماس بگیرید.",
            "matched": None}


# --- مدیریت سؤالات متداول (فقط مدیر) ---
class FaqIn(BaseModel):
    question: str
    answer: str


@router.get("/faq")
def list_faq(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return [{"id": f.id, "question": f.question, "answer": f.answer}
            for f in db.query(BotFaq).order_by(BotFaq.id).all()]


@router.post("/faq")
def create_faq(data: FaqIn, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    f = BotFaq(question=data.question.strip(), answer=data.answer.strip())
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"id": f.id}


@router.put("/faq/{faq_id}")
def update_faq(faq_id: int, data: FaqIn, db: Session = Depends(get_db),
               _admin: User = Depends(require_admin)):
    f = db.get(BotFaq, faq_id)
    if not f:
        raise HTTPException(404, "یافت نشد")
    f.question, f.answer = data.question.strip(), data.answer.strip()
    db.commit()
    return {"ok": True}


@router.delete("/faq/{faq_id}")
def delete_faq(faq_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    f = db.get(BotFaq, faq_id)
    if not f:
        raise HTTPException(404, "یافت نشد")
    db.delete(f)
    db.commit()
    return {"ok": True}