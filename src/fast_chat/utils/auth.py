from datetime import datetime, timedelta, UTC
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from config import settings

password_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__rounds=12,
    argon2__memory_cost=65536,
    argon2__parallelism=2,
)


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt
