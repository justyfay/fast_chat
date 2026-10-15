from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator

from fast_chat.config import settings
from fast_chat.utils.password_policy import validate_password


class UserSchema(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: str


class UserRegisterSchema(BaseModel):
    email: EmailStr
    full_name: str
    telegram_unic_code: str
    password: str
    repeat_password: str

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        problems = validate_password(value, strict=settings.password_policy_strict)
        if problems:
            raise ValueError("Пароль не подходит: " + "; ".join(problems))
        return value


class UserLoginResponseSchema(BaseModel):
    access_token: str
