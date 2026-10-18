from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from fast_chat.config import settings
from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.database import get_session
from fast_chat.dependencies.redis import get_redis
from fast_chat.exceptions import (
    ServiceUnavailable,
    TokenNoFoundException,
    TokenExpiredException,
    TokenRevokedException,
    NoFoundUserException,
)
from fast_chat.utils.token_revocation import is_token_revoked

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_token(request: Request):
    """
    Метод извлекает JWT из cookie `access_token`.

    Если cookie нет, выдвет исключение.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise TokenNoFoundException
    return token


async def get_current_user(
    token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    """
    Метод определяет текущего пользователя по JWT из cookie для HTTP-запросов.

    Возвращает строку с пользователем из БД (все колонки).
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except ExpiredSignatureError:
        raise TokenExpiredException
    except JWTError as e:
        if str(e) == "Not enough segments":
            raise HTTPException(
                detail="Wrong Token or missing", status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            raise HTTPException(
                detail="Not manager authenticated error",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    username: str = payload.get("sub")
    if not username:
        raise NoFoundUserException

    jti: str | None = payload.get("jti")
    sid: str | None = payload.get("sid")
    if not jti or not sid or await is_token_revoked(redis, jti, sid):
        raise TokenRevokedException

    user = await UserDAO.find_one_or_none(db_session=session, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_ws_user(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    """
    Метод определяет пользователя по cookie при подключении к WebSocket.
    """
    token = websocket.cookies.get("access_token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    username: str | None = payload.get("sub")
    if not username:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    jti: str | None = payload.get("jti")
    sid: str | None = payload.get("sid")
    if not jti or not sid:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    try:
        revoked = await is_token_revoked(redis, jti, sid)
    except ServiceUnavailable:
        raise WebSocketException(code=status.WS_1013_TRY_AGAIN_LATER)
    if revoked:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    user = await UserDAO.find_one_or_none(db_session=session, username=username)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return user
