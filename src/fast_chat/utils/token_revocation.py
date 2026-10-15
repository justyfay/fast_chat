import time

from redis.asyncio import Redis
from redis.exceptions import RedisError

from fast_chat.constants import AuthData
from fast_chat.exceptions import ServiceUnavailable
from fast_chat.logger import get_logger

logger = get_logger()


async def revoke_token(redis: Redis, jti: str, exp: int) -> None:
    """Метод кладёт `jti` токен в Redis на время, оставшееся до истечения токена, а затем отзывает."""
    ttl = max(exp - int(time.time()), 1)
    try:
        await redis.set(AuthData.REVOKED_TOKEN_KEY.format(jti=jti), 1, ex=ttl)
    except (RedisError, OSError):
        logger.exception("[auth] Redis недоступен, токен не отозван.")
        raise ServiceUnavailable


async def is_token_revoked(redis: Redis, jti: str) -> bool:
    """Метод проверяет, отозван ли токен."""
    try:
        return bool(await redis.exists(AuthData.REVOKED_TOKEN_KEY.format(jti=jti)))
    except (RedisError, OSError):
        logger.exception("[auth] Redis недоступен, отзыв токена не проверить.")
        raise ServiceUnavailable
