from __future__ import annotations

from asyncio import current_task

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings
from logger import get_logger

logger = get_logger()


class Base(DeclarativeBase):
    """Класс аккумуляции данных всех таблиц для работы с миграциями."""


class DatabaseSessionManager:
    """Класс для работы с подключениями к базе."""

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_maker = None
        self.session = None

    def connect(self):
        self.engine = create_async_engine(
            settings.database_url, pool_size=100, max_overflow=0, pool_pre_ping=False
        )
        self.session_maker = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.session = async_scoped_session(self.session_maker, scopefunc=current_task)

    async def close(self):
        if self.engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self.engine.dispose()


sessionmanager = DatabaseSessionManager()
