from __future__ import annotations

from redis.asyncio import Redis

from fast_chat.config import settings


class RedisManager:
    """Клиент Redis одного воркера приложения, общий для всех его запросов.

    Создаётся при старте воркера и закрывается при остановке. У каждого воркера свой клиент,
    но все они подключаются к одному серверу Redis и видят одни и те же ключи.
    """

    def __init__(self):
        self.client: Redis | None = None

    def connect(self) -> None:
        """Создаёт клиент. Повторный вызов ничего не делает."""
        if self.client is not None:
            return
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        """Закрывает пул соединений. Повторный вызов ничего не делает."""
        if self.client is None:
            return
        await self.client.aclose()
        self.client = None


redis_manager = RedisManager()
