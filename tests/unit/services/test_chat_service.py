import pytest

from fast_chat.exceptions import CannotAddYourself, ConversationNotFound, UserNotFound
from fast_chat.services.chat import ChatService

ALISSON, COURTOIS, DE_GEA = 1, 2, 3
UNKNOWN_USER = 99


async def test_error_add_yourself(chat_service: ChatService) -> None:
    """Нельзя добавить в чаты самого себя"""
    # Act / Assert
    with pytest.raises(CannotAddYourself):
        await chat_service.add(ALISSON, ALISSON)


async def test_error_add_unknown_user(
    chat_service: ChatService,
) -> None:
    """Нельзя добавить в чаты несуществующего пользователя"""
    # Act / Assert
    with pytest.raises(UserNotFound):
        await chat_service.add(ALISSON, UNKNOWN_USER)


async def test_add_twice_returns_false_second_time(
    chat_service: ChatService,
) -> None:
    """Повторное добавление того же собеседника ничего не меняет и возвращает False"""
    # Act
    first = await chat_service.add(ALISSON, COURTOIS)
    second = await chat_service.add(ALISSON, COURTOIS)

    # Assert
    assert (first, second) == (True, False)
    partners = await chat_service.get_partners(ALISSON)
    assert [p["id"] for p in partners] == [COURTOIS]


async def test_error_delete_missing_chat(
    chat_service: ChatService,
) -> None:
    """Удаление отсутствующего чата даёт ошибку"""
    # Act / Assert
    with pytest.raises(ConversationNotFound):
        await chat_service.delete(ALISSON, COURTOIS)


async def test_delete_removes_partner(
    chat_service: ChatService,
) -> None:
    """После удаления чата собеседник пропадает из списка"""
    # Arrange
    await chat_service.add(ALISSON, COURTOIS)

    # Act
    await chat_service.delete(ALISSON, COURTOIS)

    # Assert
    assert await chat_service.get_partners(ALISSON) == []


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        pytest.param("", [COURTOIS, DE_GEA], id="empty-query"),
        pytest.param("COURT", [COURTOIS], id="case-insensitive"),
        pytest.param("de g", [DE_GEA], id="part-with-space"),
        pytest.param("nobody", [], id="nothing-found"),
    ],
)
async def test_search_available_filters_by_name(
    query: str, expected_ids: list[int], chat_service: ChatService
) -> None:
    """Поиск доступных пользователей фильтрует по части имени без учёта регистра"""
    # Act
    found = await chat_service.search_available(ALISSON, query)

    # Assert
    assert [u["id"] for u in found] == expected_ids


async def test_add_makes_chat_visible_to_both_users(
    chat_service: ChatService,
) -> None:
    """Добавленный в чаты собеседник видит чат в своём списке тоже"""
    # Act
    await chat_service.add(ALISSON, COURTOIS)

    # Assert
    assert [p["id"] for p in await chat_service.get_partners(COURTOIS)] == [ALISSON]


async def test_delete_removes_chat_only_from_own_list(
    chat_service: ChatService,
) -> None:
    """Удаление чата из списка не убирает его у собеседника"""
    # Arrange
    await chat_service.add(ALISSON, COURTOIS)

    # Act
    await chat_service.delete(ALISSON, COURTOIS)

    # Assert
    assert await chat_service.get_partners(ALISSON) == []
    assert [p["id"] for p in await chat_service.get_partners(COURTOIS)] == [ALISSON]
