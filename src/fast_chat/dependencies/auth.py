from datetime import timezone, datetime

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from fast_chat.config import settings
from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.database import get_session
from fast_chat.exceptions import (
    TokenNoFoundException,
    TokenExpiredException,
    NoFoundUserException,
)

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
    token: str = Depends(get_token), session: AsyncSession = Depends(get_session)
):
    """
    Метод определяет текущего пользователя по JWT из cookie для HTTP-запросов.

    Возвращает строку с пользователем из БД (все колонки).
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except JWTError as e:
        if str(e) == "Signature has expired.":
            raise HTTPException(
                detail="Signature has expired.", status_code=status.HTTP_400_BAD_REQUEST
            )
        elif str(e) == "Not enough segments":
            raise HTTPException(
                detail="Wrong Token or missing", status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            raise HTTPException(
                detail="Not manager authenticated error",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    expire: str = payload.get("exp")
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        raise TokenExpiredException
    username: str = payload.get("sub")
    if not username:
        raise NoFoundUserException

    user = await UserDAO.find_one_or_none(db_session=session, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_ws_user(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
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

    user = await UserDAO.find_one_or_none(db_session=session, username=username)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return user
