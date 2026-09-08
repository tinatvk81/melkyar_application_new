from typing import Optional

from pydantic import BaseModel

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.agent
    phone: Optional[str] = None  # برای دریافت یادآوری پیامکی قراردادهای رو‌به‌اتمام


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    phone: Optional[str] = None
    commission_rates: dict | None = None

    class Config:
        from_attributes = True


class UserUpdatePhone(BaseModel):
    phone: Optional[str] = None


class PasswordReset(BaseModel):
    new_password: str
