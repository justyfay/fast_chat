from typing import AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def build_get_session(engine: AsyncEngine) -> Callable[[], AsyncIterator[AsyncSession]]:
    """Тестовая замена `get_session`: тот же жизненный цикл сессии, но на engine теста."""
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
