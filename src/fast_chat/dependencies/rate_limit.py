from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from fast_chat.config import settings
from fast_chat.dependencies.redis import get_redis
from fast_chat.exceptions import ServiceUnavailable, TooManyRequests
from fast_chat.logger import get_logger

logger = get_logger()


class RateLimiter:
    """Ограничение частоты запросов: определенное количество попыток на заданный интервал.

    Счётчик на каждый IP лежит в Redis и общий для всех воркеров. Интервал фиксированный,
    начинается с первой попытки и сбрасывается по истечении TTL ключа.
    """

    def __init__(self, name: str, attempts: int, interval_seconds: int):
        self.name = name
        self.attempts = attempts
        self.interval_seconds = interval_seconds

    def key(self, identifier: str) -> str:
        return f"rl:{self.name}:{identifier}"

    async def check(self, redis: Redis, identifier: str) -> None:
        """Учитывает попытку. Если лимит превышен, бросает `TooManyRequests`."""
        key = self.key(identifier)
        try:
            # Одна транзакция, чтобы параллельные запросы не обгоняли друг друга
            async with redis.pipeline(transaction=True) as pipe:
                pipe.set(key, 0, ex=self.interval_seconds, nx=True)
                pipe.incr(key)
                pipe.ttl(key)
                _, count, ttl = await pipe.execute()
            if ttl < 0:
                await redis.expire(key, self.interval_seconds)
                ttl = self.interval_seconds
        except (RedisError, OSError):
            logger.exception(f"[rate_limit] {self.name}: Redis недоступен.")
            raise ServiceUnavailable

        if count > self.attempts:
            logger.debug(
                f"[rate_limit] {self.name}: лимит превышен для '{identifier}'."
            )
            raise TooManyRequests(retry_after=max(ttl, 1))

    async def __call__(self, request: Request, redis: Redis = Depends(get_redis)):
        identifier = request.client.host if request.client else "unknown"
        await self.check(redis, identifier)


login_rate_limit = RateLimiter(
    "login",
    settings.rate_limit_auth_attempts,
    settings.rate_limit_auth_seconds,
)
register_rate_limit = RateLimiter(
    "register",
    settings.rate_limit_auth_attempts,
    settings.rate_limit_auth_seconds,
)
refresh_rate_limit = RateLimiter(
    "refresh",
    settings.rate_limit_auth_attempts * 6,
    settings.rate_limit_auth_seconds,
)
