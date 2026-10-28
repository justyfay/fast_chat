import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from redis.asyncio import Redis

from fast_chat.config import settings
from fast_chat.dao.user import UserDAO
from fast_chat.exceptions import (
    RefreshTokenInvalidException,
    UserAlreadyExists,
    UserIncorrectCredentials,
    UserPasswordsNotEqual,
)
from fast_chat.schemas.user import UserRegisterSchema, UserSchema
from fast_chat.utils.auth import (
    create_access_token,
    get_hashed_password,
    verify_password,
)
from fast_chat.utils.refresh_tokens import (
    end_session,
    get_refresh_session_id,
    issue_refresh_token,
    rotate_refresh_token,
)
from fast_chat.utils.token_revocation import revoke_token


class AuthService:
    """Регистрация, вход, обновление и завершение сессии."""

    def __init__(self, users: UserDAO, redis: Redis) -> None:
        """
        :param users: DAO пользователей
        :param redis: Экземпляр клиента Redis
        """
        self.users = users
        self.redis = redis

    @staticmethod
    def _create_access_token(username: str, sid: str) -> str:
        """
        Выпускает access-токен сессии.

        :param username: Имя пользователя
        :param sid: Идентификатор сессии
        """
        return create_access_token(
            data={"sub": username, "sid": sid},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

    async def register(self, data: UserRegisterSchema) -> UserSchema:
        """
        Регистрирует пользователя.

        :param data: Данные регистрации.
        """
        if await self.users.find_one_or_none(username=data.email):
            raise UserAlreadyExists
        if data.password.encode() != data.repeat_password.encode():
            raise UserPasswordsNotEqual

        created_user = await self.users.add(
            username=data.email,
            telegram_unic_code=int(data.telegram_unic_code)
            if data.telegram_unic_code != ""
            else None,
            email=data.email,
            full_name=data.full_name,
            hashed_password=get_hashed_password(data.password),
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        return UserSchema.model_construct(
            id=created_user["id"],
            email=data.email,
            username=data.email,
            full_name=data.full_name,
        )

    async def login(self, username: str, password: str) -> tuple[str, str]:
        """
        Проверяет пароль и начинает новую сессию. Возвращает access и refresh-токены.

        :param username: Имя пользователя (email)
        :param password: Пароль в открытом виде
        """
        current_user = await self.users.find_one_or_none(username=username)
        if not current_user or not verify_password(
            password, current_user["hashed_password"]
        ):
            raise UserIncorrectCredentials

        sid = uuid.uuid4().hex
        access_token = self._create_access_token(username, sid)
        refresh_token = await issue_refresh_token(self.redis, username, sid)
        return access_token, refresh_token

    async def refresh(self, refresh_token: str | None) -> tuple[str, str]:
        """
        Обменивает refresh-токен на новую пару токенов той же сессии.

        :param refresh_token: Refresh-токен из cookie (может отсутствовать).
        """
        if not refresh_token:
            raise RefreshTokenInvalidException
        username, sid, new_refresh_token = await rotate_refresh_token(
            self.redis, refresh_token
        )
        if not await self.users.find_one_or_none(username=username):
            await end_session(self.redis, sid)
            raise RefreshTokenInvalidException
        return self._create_access_token(username, sid), new_refresh_token

    async def logout(self, access_token: str | None, refresh_token: str | None) -> None:
        """
        Завершает сессию по access (может быть просрочен) и refresh-токенам из cookie.

        :param access_token: Access-токен из cookie, может отсутствовать
        :param refresh_token: Refresh-токен из cookie, может отсутствовать
        """
        sids = set()
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
                await revoke_token(self.redis, payload["jti"], payload["exp"])
            if payload.get("sid"):
                sids.add(payload["sid"])
        if refresh_token and (
            sid := await get_refresh_session_id(self.redis, refresh_token)
        ):
            sids.add(sid)
        for sid in sids:
            await end_session(self.redis, sid)
