from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from src.fast_chat.database import sessionmanager
from src.fast_chat.exceptions import FailedDbSession


async def get_session() -> AsyncIterator[AsyncSession]:
    """Метод зависимости (Depends), управляющий жизненным циклом сеанса БД."""
    sessionmanager.connect()
    session = sessionmanager.session()
    if session is None:
        raise FailedDbSession
    try:
        yield session
        await session.commit()
    except (Exception, OSError):
        await session.rollback()
        raise
    finally:
        await session.close()
