import uuid
from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Request, Response, Depends
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from redis.asyncio import Redis
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.config import settings
from fast_chat.constants import AuthData
from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.auth import get_session
from fast_chat.dependencies.rate_limit import (
    login_rate_limit,
    refresh_rate_limit,
    register_rate_limit,
)
from fast_chat.dependencies.redis import get_redis
from fast_chat.exceptions import (
    RefreshTokenInvalidException,
    UserAlreadyExists,
    UserPasswordsNotEqual,
    UserIncorrectCredentials,
)
from fast_chat.schemas.user import (
    UserRegisterSchema,
    UserSchema,
    UserLoginResponseSchema,
)

from fast_chat.utils.auth import (
    verify_password,
    create_access_token,
    get_hashed_password,
)
from fast_chat.utils.refresh_tokens import (
    end_session,
    get_refresh_session_id,
    issue_refresh_token,
    refresh_ttl,
    rotate_refresh_token,
)
from fast_chat.utils.token_revocation import revoke_token

auth_router = APIRouter(prefix="/auth", tags=["Авторизация"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Обе cookie живут до истечения срока жизни refresh-токена,
    просроченный access обновляется через `/auth/refresh`.

    :param response: Ответ сервера, в который записываются cookie
    :param access_token: Access-токен (JWT)
    :param refresh_token: Refresh-токен в открытом виде
    """
    max_age = refresh_ttl()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=max_age,
    )
    response.set_cookie(
        key=AuthData.REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=max_age,
        path=AuthData.REFRESH_COOKIE_PATH,
    )


@auth_router.post("/register", dependencies=[Depends(register_rate_limit)])
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


@auth_router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login_user(
    response: Response,
    user: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> UserLoginResponseSchema:
    current_user: RowMapping = await UserDAO.find_one_or_none(
        session, username=user.username
    )
    if not current_user or not verify_password(
        user.password, current_user["hashed_password"]
    ):
        raise UserIncorrectCredentials

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    sid = uuid.uuid4().hex
    access_token = create_access_token(
        data={"sub": user.username, "sid": sid}, expires_delta=access_token_expires
    )
    refresh_token = await issue_refresh_token(redis, user.username, sid)
    set_auth_cookies(response, access_token, refresh_token)
    return UserLoginResponseSchema(access_token=access_token)


@auth_router.post(
    "/refresh",
    dependencies=[Depends(refresh_rate_limit)],
    description="Обновляет сессию по refresh-токену из cookie: выдаёт новую пару токенов.",
)
async def refresh_session(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> UserLoginResponseSchema:
    refresh_token = request.cookies.get(AuthData.REFRESH_COOKIE)
    if not refresh_token:
        raise RefreshTokenInvalidException
    username, sid, new_refresh_token = await rotate_refresh_token(redis, refresh_token)
    if not await UserDAO.find_one_or_none(session, username=username):
        await end_session(redis, sid)
        raise RefreshTokenInvalidException
    access_token = create_access_token(
        data={"sub": username, "sid": sid},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    set_auth_cookies(response, access_token, new_refresh_token)
    return UserLoginResponseSchema(access_token=access_token)


@auth_router.post("/logout")
async def logout_user(
    request: Request, response: Response, redis: Redis = Depends(get_redis)
):
    sids = set()
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            payload = jwt.decode(
                access_token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": False},
            )
        except JWTError:
            payload = {}
        if payload.get("jti"):
            await revoke_token(redis, payload["jti"], payload["exp"])
        if payload.get("sid"):
            sids.add(payload["sid"])
    refresh_token = request.cookies.get(AuthData.REFRESH_COOKIE)
    if refresh_token and (sid := await get_refresh_session_id(redis, refresh_token)):
        sids.add(sid)
    for sid in sids:
        await end_session(redis, sid)
    response.delete_cookie(key="access_token")
    response.delete_cookie(
        key=AuthData.REFRESH_COOKIE, path=AuthData.REFRESH_COOKIE_PATH
    )
    return {"message": "Пользователь успешно вышел из системы"}
