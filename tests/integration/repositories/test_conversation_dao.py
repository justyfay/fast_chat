from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.conversation import ConversationDAO
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


async def test_add_duplicate_conversation(
    db_session: AsyncSession,
) -> None:
    """Добавление беседы возвращает True, повторное добавление той же беседы возвращает False"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")

    # Act
    first = await ConversationDAO.add_conversation(db_session, user_one, user_two)
    second = await ConversationDAO.add_conversation(db_session, user_one, user_two)

    # Assert
    assert first is True
    assert second is False


async def test_partners_priority_list(
    db_session: AsyncSession,
) -> None:
    """Список собеседников возвращается в порядке добавления бесед"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    user_three = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    await ConversationDAO.add_conversation(db_session, user_one, user_three)
    await ConversationDAO.add_conversation(db_session, user_one, user_two)

    # Act
    partners = await ConversationDAO.get_partners(db_session, user_one)

    # Assert
    assert [p["id"] for p in partners] == [user_three, user_two]


async def test_get_available_users_excludes_self_and_partners(
    db_session: AsyncSession,
) -> None:
    """
    Доступные для добавления пользователи не включают
    самого пользователя и уже добавленных собеседников
    """
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    user_three = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    await ConversationDAO.add_conversation(db_session, user_one, user_two)

    # Act
    available = await ConversationDAO.get_available_users(db_session, user_one)

    # Assert
    assert [u["id"] for u in available] == [user_three]


async def test_delete_missing_conversation(
    db_session: AsyncSession,
) -> None:
    """Удаление отсутствующей беседы возвращает False"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")

    # Act
    deleted = await ConversationDAO.delete_conversation(db_session, user_one, user_two)

    # Assert
    assert deleted is False
