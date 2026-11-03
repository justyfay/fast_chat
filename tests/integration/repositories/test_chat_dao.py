from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.chat import ChatDAO
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


async def test_direct_chat_is_one_per_pair(db_session: AsyncSession) -> None:
    """Личный чат пары один, независимо от того, кто из двоих его создаёт"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    chats = ChatDAO(db_session)

    # Act
    first = await chats.get_or_create_direct(user_one, user_two)
    second = await chats.get_or_create_direct(user_two, user_one)

    # Assert
    assert first == second
    assert await chats.find_direct(user_one, user_two) == first


async def test_find_direct_returns_none_without_chat(db_session: AsyncSession) -> None:
    """Если личного чата у пары нет, поиск возвращает None"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")

    # Act / Assert
    assert await ChatDAO(db_session).find_direct(user_one, user_two) is None


async def test_add_member_twice(db_session: AsyncSession) -> None:
    """Добавление участника возвращает True, повторное добавление того же участника возвращает False"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    chats = ChatDAO(db_session)
    chat_id = await chats.get_or_create_direct(user_one, user_two)

    # Act
    first = await chats.add_member(chat_id, user_one)
    second = await chats.add_member(chat_id, user_one)

    # Assert
    assert (first, second) == (True, False)


async def test_partners_priority_list(db_session: AsyncSession) -> None:
    """Список собеседников возвращается в порядке добавления чатов"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    user_three = await _add_user(db_session, "David de Gea", "de.gea@example.com")
    chats = ChatDAO(db_session)
    for partner in (user_three, user_two):
        chat_id = await chats.get_or_create_direct(user_one, partner)
        await chats.add_member(chat_id, user_one)
        await chats.add_member(chat_id, partner)

    # Act
    partners = await chats.get_partners(user_one)

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
    chats = ChatDAO(db_session)
    chat_id = await chats.get_or_create_direct(user_one, user_two)
    await chats.add_member(chat_id, user_one)
    await chats.add_member(chat_id, user_two)

    # Act
    available = await chats.get_available_users(user_one)

    # Assert
    assert [u["id"] for u in available] == [user_three]


async def test_remove_member_keeps_chat_for_partner(db_session: AsyncSession) -> None:
    """Выход участника не убирает чат у собеседника"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    chats = ChatDAO(db_session)
    chat_id = await chats.get_or_create_direct(user_one, user_two)
    await chats.add_member(chat_id, user_one)
    await chats.add_member(chat_id, user_two)

    # Act
    removed = await chats.remove_member(chat_id, user_one)

    # Assert
    assert removed is True
    assert await chats.get_partners(user_one) == []
    assert [p["id"] for p in await chats.get_partners(user_two)] == [user_one]


async def test_remove_missing_member(db_session: AsyncSession) -> None:
    """Удаление отсутствующего участника возвращает False"""
    # Arrange
    user_one = await _add_user(db_session, "Alisson Becker", "alisson@example.com")
    user_two = await _add_user(db_session, "Thibaut Courtois", "courtois@example.com")
    chats = ChatDAO(db_session)
    chat_id = await chats.get_or_create_direct(user_one, user_two)

    # Act / Assert
    assert await chats.remove_member(chat_id, user_one) is False
