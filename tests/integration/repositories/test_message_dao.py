from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.message import MessageDAO
from fast_chat.dao.user import UserDAO


async def _add_user(db_session: AsyncSession, full_name: str, email: str) -> int:
    created = await UserDAO(db_session).add(
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
    """Выборка сообщений между двумя пользователями возвращает только их диалог."""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    de_gea = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    await MessageDAO(db_session).add(
        sender_id=user_one, recipient_id=user_two, body="1"
    )
    await MessageDAO(db_session).add(
        sender_id=user_two, recipient_id=user_one, body="2"
    )
    await MessageDAO(db_session).add(sender_id=user_one, recipient_id=de_gea, body="x")

    # Act
    messages = await MessageDAO(db_session).get_messages_between_users(
        user_one, user_two
    )

    # Assert
    assert [m.body for m in messages] == ["1", "2"]


async def test_error_add_message_for_unknown_users(db_session: AsyncSession) -> None:
    """Ошибка БД отображается при добавлении невалидного сообщения."""
    # Act / Assert
    with pytest.raises(IntegrityError):
        await MessageDAO(db_session).add(sender_id=1, recipient_id=2, body="no users")


async def test_error_find_by_forbidden_field(db_session: AsyncSession) -> None:
    """Нельзя искать по колонке, если она не разрешена."""
    # Act / Assert
    with pytest.raises(ValueError, match="body"):
        await MessageDAO(db_session).find_one_or_none(body="secret")
