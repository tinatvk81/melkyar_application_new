"""
هش کردن رمز عبور و ساخت/بررسی توکن JWT.
نکته‌ی امنیتی مهم: هیچ رمز عبوری هرگز به‌صورت متن ساده ذخیره نمی‌شود.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, user_id: int, role: str, token_version: int) -> str:
    """
    token_version در دیتابیس کاربر ذخیره می‌شود. اگر مدیر رمز کاربری را ریست کند
    یا او را غیرفعال کند، token_version را +۱ می‌کنیم؛ در نتیجه توکن‌های قبلی
    (حتی اگر لپ‌تاپ گم شده باشد) فوراً بی‌اعتبار می‌شوند — بدون نیاز به فراخوانی
    از سمت کلاینت.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "tv": token_version, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
