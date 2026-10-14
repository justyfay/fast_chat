from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from fast_chat.config import settings
from fast_chat.logger import get_logger

logger = get_logger()

POOL_SIZE = 10
MAX_OVERFLOW = 10


class Base(DeclarativeBase):
    """Класс аккумуляции данных всех таблиц для работы с миграциями."""


class DatabaseSessionManager:
    """Класс для работы с подключениями к базе.

    Engine и пул соединений создаются один раз при старте приложения (`lifespan`)
    и закрываются при его остановке.
    """

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_maker: async_sessionmaker[AsyncSession] | None = None

    def connect(self) -> None:
        """Метод создаёт engine и фабрику сессий. Повторный вызов ничего не делает."""
        if self.engine is not None:
            return
        self.engine = create_async_engine(
            settings.database_url,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_pre_ping=True,
        )
        self.session_maker = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    async def close(self) -> None:
        """Метод закрывает пул соединений. Повторный вызов безопасен."""
        if self.engine is None:
            return
        await self.engine.dispose()
        self.engine = None
        self.session_maker = None


sessionmanager = DatabaseSessionManager()
