from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, PasswordReset, UserUpdatePhone
from app.services.activity_log_service import log_activity
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/", response_model=UserRead)
def create_agent(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="این نام کاربری قبلاً استفاده شده است")
    user = User(
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "create", "user", user.id, detail=f"{user.username} ({user.role.value})")
    return user


@router.put("/{user_id}/phone", response_model=UserRead)
def update_phone(
    user_id: int, data: UserUpdatePhone, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """برای فعال‌سازی یادآوری پیامکی، هر مشاور باید یک شماره تلفن ثبت‌شده داشته باشد."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
    user.phone = data.phone
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "update_phone", "user", user.id, detail=user.username)
    return user


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
    user.is_active = False
    user.token_version += 1  # هر توکن باز فعلی این کاربر فوراً باطل می‌شود
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "deactivate", "user", user.id, detail=user.username)
    return user


@router.post("/{user_id}/activate", response_model=UserRead)
def activate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
    user.is_active = True
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "activate", "user", user.id, detail=user.username)
    return user


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_password(
    user_id: int, data: PasswordReset, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
    user.hashed_password = hash_password(data.new_password)
    user.token_version += 1  # نشست‌های فعال قبلی با این کار باطل می‌شوند
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "reset_password", "user", user.id, detail=user.username)
    return user



class CommissionRatesIn(BaseModel):
    rates: dict  # مثال: {"sale": 45, "rent": 10, "presale": 30, "mortgage": 8}

@router.put("/{user_id}/commission-rates", response_model=UserRead)
def set_commission_rates(user_id: int, data: CommissionRatesIn,
                         db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "کاربر پیدا نشد")
    user.commission_rates = data.rates
    db.commit()
    db.refresh(user)
    log_activity(db, admin.id, "update", "user", user.id, detail=f"درصد پورسانت {user.username}")
    return user