from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fast_chat.database import sessionmanager
from fast_chat.exceptions import FailedDbSession


async def get_session() -> AsyncIterator[AsyncSession]:
    """Метод зависимости, управляющий жизненным циклом сеанса БД (Один запрос - одна транзакция)."""
    if sessionmanager.session_maker is None:
        raise FailedDbSession
    session = sessionmanager.session_maker()
    try:
        yield session
        await session.commit()
    except (Exception, OSError):
        await session.rollback()
        raise
    finally:
        await session.close()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Метод зависимости, возвращающий фабрику сессий для долгоживущих соединений (Websockets).
    """
    if sessionmanager.session_maker is None:
        raise FailedDbSession
    return sessionmanager.session_maker
