from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Response, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from src.fast_chat.dao.user import UserDAO
from src.fast_chat.dependencies.auth import get_session
from src.fast_chat.exceptions import (
    UserAlreadyExists,
    UserPasswordsNotEqual,
    UserIncorrectCredentials,
)
from src.fast_chat.schemas.user import (
    UserRegisterSchema,
    UserSchema,
    UserLoginResponseSchema,
)

from src.fast_chat.utils.auth import (
    verify_password,
    create_access_token,
    get_hashed_password,
)

auth_router = APIRouter(prefix="/auth", tags=["Авторизация"])


@auth_router.post("/register")
async def register_user(
    user: UserRegisterSchema, session: AsyncSession = Depends(get_session)
):
    current_user: RowMapping = await UserDAO.find_one_or_none(
        session, username=user.email
    )

    if current_user:
        raise UserAlreadyExists
    if user.password.encode() != user.repeat_password.encode():
        raise UserPasswordsNotEqual

    hashed_password = get_hashed_password(user.password)

    created_user = await UserDAO.add(
        db_session=session,
        username=user.email,
        telegram_unic_code=int(user.telegram_unic_code)
        if user.telegram_unic_code != ""
        else None,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )

    return UserSchema.model_construct(
        id=created_user["id"],
        email=user.email,
        username=user.email,
        full_name=user.full_name,
    )


@auth_router.post("/login")
async def login_user(
    response: Response,
    user: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> UserLoginResponseSchema:
    current_user: RowMapping = await UserDAO.find_one_or_none(
        session, username=user.username
    )
    if not current_user or not verify_password(
        user.password, current_user["hashed_password"]
    ):
        raise UserIncorrectCredentials

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return UserLoginResponseSchema(access_token=access_token)


@auth_router.post("/logout")
async def logout_user(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Пользователь успешно вышел из системы"}
