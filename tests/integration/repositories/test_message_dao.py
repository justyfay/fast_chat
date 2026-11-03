from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.chat import ChatDAO
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


async def test_get_chat_messages_returns_only_this_chat(
    db_session: AsyncSession,
) -> None:
    """Выборка сообщений чата возвращает только его сообщения по возрастанию id"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    de_gea = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    chats = ChatDAO(db_session)
    chat_id = await chats.get_or_create_direct(user_one, user_two)
    other_chat_id = await chats.get_or_create_direct(user_one, de_gea)
    messages = MessageDAO(db_session)
    await messages.add(chat_id=chat_id, sender_id=user_one, body="1")
    await messages.add(chat_id=chat_id, sender_id=user_two, body="2")
    await messages.add(chat_id=other_chat_id, sender_id=user_one, body="x")

    # Act
    result = await messages.get_chat_messages(chat_id)

    # Assert
    assert [m.body for m in result] == ["1", "2"]


async def test_error_add_message_to_unknown_chat(db_session: AsyncSession) -> None:
    """Ошибка БД отображается при добавлении невалидного сообщения."""
    # Act / Assert
    with pytest.raises(IntegrityError):
        await MessageDAO(db_session).add(chat_id=1, sender_id=1, body="no chat")


async def test_error_find_by_forbidden_field(db_session: AsyncSession) -> None:
    """Нельзя искать по колонке, если она не разрешена."""
    # Act / Assert
    with pytest.raises(ValueError, match="body"):
        await MessageDAO(db_session).find_one_or_none(body="secret")
