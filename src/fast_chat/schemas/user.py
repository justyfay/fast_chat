from __future__ import annotations

from pydantic import BaseModel, EmailStr


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


class UserLoginResponseSchema(BaseModel):
    access_token: str
