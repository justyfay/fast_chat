import time
from contextlib import contextmanager
from typing import Iterator

from redis.asyncio import Redis
from redis.exceptions import RedisError

from fast_chat.config import settings
from fast_chat.constants import AuthData
from fast_chat.exceptions import ServiceUnavailable
from fast_chat.logger import get_logger

logger = get_logger()


@contextmanager
def check_redis_available() -> Iterator[None]:
    """Если Redis недоступен, метод вернет 503."""
    try:
        yield
    except (RedisError, OSError):
        logger.exception("[auth] Redis недоступен.")
        raise ServiceUnavailable


async def revoke_token(redis: Redis, jti: str, exp: int) -> None:
    """
    Метод кладёт `jti` токен в Redis на время, оставшееся до истечения токена, а затем отзывает.

    :param redis: Экземпляр клиента Redis
    :param jti: Уникальный идентификатор отзываемого токена
    :param exp: Время истечения токена в секундах
    """
    ttl = max(exp - int(time.time()), 1)
    with check_redis_available():
        await redis.set(AuthData.REVOKED_TOKEN_KEY.format(jti=jti), 1, ex=ttl)


async def revoke_session(redis: Redis, sid: str) -> None:
    """
    Метод отзывает сессию, access-токены в сессии перестают работать.

    :param redis: Экземпляр клиента Redis
    :param sid: Идентификатор отзываемой сессии
    """
    ttl = settings.access_token_expire_minutes * 60
    with check_redis_available():
        await redis.set(AuthData.REVOKED_SESSION_KEY.format(sid=sid), 1, ex=ttl)


async def is_token_revoked(redis: Redis, jti: str, sid: str) -> bool:
    """
    Метод проверяет, отозван ли токен или его сессия.

    :param redis: Экземпляр клиента Redis
    :param jti: Уникальный идентификатор проверяемого токена
    :param sid: Идентификатор сессии токена
    """
    with check_redis_available():
        return bool(
            await redis.exists(
                AuthData.REVOKED_TOKEN_KEY.format(jti=jti),
                AuthData.REVOKED_SESSION_KEY.format(sid=sid),
            )
        )
