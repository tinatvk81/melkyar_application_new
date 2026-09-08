from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import Token
from app.services.activity_log_service import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 3
LOCK_MINUTES = 2


def _is_admin(user: User) -> bool:
    return getattr(user.role, "value", str(user.role)) == "admin"


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()

    now = datetime.now(timezone.utc)
    if user and user.locked_until:
        locked_until = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            remaining = int((locked_until - now).total_seconds()) + 1
            raise HTTPException(status_code=423, detail=f"حساب موقتاً قفل شده است. {remaining} ثانیه دیگر دوباره تلاش کنید.")
        user.locked_until = None
        user.failed_attempts = 0
        db.commit()

    if not user or not verify_password(form_data.password, user.hashed_password):
        # مدیر نامحدود تلاش می‌کند؛ سایر کاربران بعد از ۳ بار اشتباه ۲ دقیقه قفل می‌شوند
        if user and not _is_admin(user):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= MAX_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
                user.failed_attempts = 0
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور اشتباه است")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="این حساب غیرفعال شده است")

    if user.failed_attempts or user.locked_until:
        user.failed_attempts = 0
        user.locked_until = None
        db.commit()

    token = create_access_token(user_id=user.id, role=user.role.value, token_version=user.token_version)
    log_activity(db, user.id, "login", "user", user.id)
    return Token(access_token=token, role=user.role.value, full_name=user.full_name)