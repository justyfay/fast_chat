from datetime import datetime

import pytest
from asyncpg import Connection
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from fast_chat.dao.message import MessageDAO
from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.database import get_session


@pytest.fixture
def work_get_session(engine: AsyncEngine, mocker: MockerFixture) -> None:
    """Настоящий `get_session` на тестовой БД."""
    mocker.patch(
        "fast_chat.dependencies.database.sessionmanager.session_maker",
        async_sessionmaker(bind=engine, autoflush=False),
    )


async def _add_user(session, email: str) -> None:
    await UserDAO(session).add(
        username=email,
        email=email,
        full_name="Alisson Becker",
        hashed_password="hash",
        telegram_unic_code=None,
        created_at=datetime(2025, 1, 1),
    )


async def test_session_commits_all_writes_at_the_end(
    pg_conn: Connection, work_get_session
) -> None:
    """Все записи запроса фиксируются одной транзакцией при завершении запроса."""
    # Arrange
    dependency = get_session()
    session = await dependency.__anext__()
    await _add_user(session, "alisson@example.com")
    await _add_user(session, "courtois@example.com")
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0

    # Act
    with pytest.raises(StopAsyncIteration):
        await dependency.__anext__()

    # Assert
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 2


async def test_session_rolls_back_all_writes_on_error(
    pg_conn: Connection, work_get_session
) -> None:
    """Если запрос завершился ошибкой, не сохраняется ни одна из его записей."""
    # Arrange
    dependency = get_session()
    session = await dependency.__anext__()
    await _add_user(session, "alisson@example.com")
    with pytest.raises(IntegrityError):
        await MessageDAO(session).add(sender_id=1, recipient_id=2, body="no users")

    # Act
    with pytest.raises(IntegrityError):
        await dependency.athrow(IntegrityError("stmt", {}, Exception()))

    # Assert
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0
