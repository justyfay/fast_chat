from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.message import MessageDAO
from fast_chat.dao.user import UserDAO


async def _add_user(db_session: AsyncSession, full_name: str, email: str) -> int:
    created = await UserDAO.add(
        db_session=db_session,
        username=email,
        email=email,
        full_name=full_name,
        hashed_password="hash",
        telegram_unic_code=None,
        created_at=datetime(2025, 1, 1),
    )
    return created["id"]


async def test_get_current_messages_between_users(
    db_session: AsyncSession,
) -> None:
    """Выборка сообщений между двумя пользователями возвращает только их диалог"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    de_gea = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    await MessageDAO.add(
        db_session=db_session, sender_id=user_one, recipient_id=user_two, body="1"
    )
    await MessageDAO.add(
        db_session=db_session, sender_id=user_two, recipient_id=user_one, body="2"
    )
    await MessageDAO.add(
        db_session=db_session, sender_id=user_one, recipient_id=de_gea, body="x"
    )

    # Act
    messages = await MessageDAO.get_messages_between_users(
        db_session, user_one, user_two
    )

    # Assert
    assert [m.body for m in messages] == ["1", "2"]


async def test_add_returns_none_on_database_error(db_session: AsyncSession) -> None:
    """При ошибке БД добавление сообщения возвращает None"""
    # TO-DO: Поправить после того, как BaseDAO.add перестанет
    # возвращать None при ошибках
    # Act
    result = await MessageDAO.add(
        db_session=db_session, sender_id=1, recipient_id=2, body="no such users"
    )

    # Assert
    assert result is None
