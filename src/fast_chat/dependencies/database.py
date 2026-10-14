from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from fast_chat.database import sessionmanager
from fast_chat.exceptions import FailedDbSession


async def get_session() -> AsyncIterator[AsyncSession]:
    """Метод зависимости (Depends), управляющий жизненным циклом сеанса БД."""
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
