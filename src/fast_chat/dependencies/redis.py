from redis.asyncio import Redis

from fast_chat.exceptions import ServiceUnavailable
from fast_chat.redis_client import redis_manager


async def get_redis() -> Redis:
    """Метод зависимости, возвращающий общий клиент Redis."""
    if redis_manager.client is None:
        raise ServiceUnavailable
    return redis_manager.client
