from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    user_id: Optional[int] = None
class LoginRequest(BaseModel):
    username: str
    password: str
