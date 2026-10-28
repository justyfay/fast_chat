from typing import AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def build_get_session(engine: AsyncEngine) -> Callable[[], AsyncIterator[AsyncSession]]:
    """Тестовый `get_session` на engine теста."""
    session_maker = async_sessionmaker(bind=engine, autoflush=False)

    async def get_test_session() -> AsyncIterator[AsyncSession]:
        session = session_maker()
        try:
            yield session
            await session.commit()
        except (Exception, OSError):
            await session.rollback()
            raise
        finally:
            await session.close()

    return get_test_session


def build_session_factory(
    engine: AsyncEngine,
) -> Callable[[], async_sessionmaker[AsyncSession]]:
    """Фабрика сессий на engine теста."""
    session_maker = async_sessionmaker(bind=engine, autoflush=False)

    def get_test_session_factory() -> async_sessionmaker[AsyncSession]:
        return session_maker

    return get_test_session_factory
