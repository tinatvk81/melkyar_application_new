from pydantic import BaseModel

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.agent


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    new_password: str
