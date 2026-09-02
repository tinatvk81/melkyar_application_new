from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="نشست شما نامعتبر است، دوباره وارد شوید",
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error

    # اگر مدیر رمز را ریست کرده یا کاربر را غیرفعال/فعال کرده باشد، token_version
    # عوض شده و توکن‌های قدیمی (حتی از لپ‌تاپ گم‌شده) این‌جا رد می‌شوند.
    if payload.get("tv") != user.token_version:
        raise credentials_error

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط مدیر به این بخش دسترسی دارد")
    return current_user
