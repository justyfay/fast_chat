import pytest

from fast_chat.exceptions import CannotAddYourself, ConversationNotFound, UserNotFound
from fast_chat.services.conversation import ConversationService

ALISSON, COURTOIS, DE_GEA = 1, 2, 3
UNKNOWN_USER = 99


async def test_error_add_yourself(conversation_service: ConversationService) -> None:
    """Нельзя добавить в беседы самого себя"""
    # Act / Assert
    with pytest.raises(CannotAddYourself):
        await conversation_service.add(ALISSON, ALISSON)


async def test_error_add_unknown_user(
    conversation_service: ConversationService,
) -> None:
    """Нельзя добавить в беседы несуществующего пользователя"""
    # Act / Assert
    with pytest.raises(UserNotFound):
        await conversation_service.add(ALISSON, UNKNOWN_USER)


async def test_add_twice_returns_false_second_time(
    conversation_service: ConversationService,
) -> None:
    """Повторное добавление того же собеседника ничего не меняет и возвращает False"""
    # Act
    first = await conversation_service.add(ALISSON, COURTOIS)
    second = await conversation_service.add(ALISSON, COURTOIS)

    # Assert
    assert (first, second) == (True, False)
    partners = await conversation_service.get_partners(ALISSON)
    assert [p["id"] for p in partners] == [COURTOIS]


async def test_error_delete_missing_conversation(
    conversation_service: ConversationService,
) -> None:
    """Удаление отсутствующей беседы даёт ошибку"""
    # Act / Assert
    with pytest.raises(ConversationNotFound):
        await conversation_service.delete(ALISSON, COURTOIS)


async def test_delete_removes_partner(
    conversation_service: ConversationService,
) -> None:
    """После удаления беседы собеседник пропадает из списка"""
    # Arrange
    await conversation_service.add(ALISSON, COURTOIS)

    # Act
    await conversation_service.delete(ALISSON, COURTOIS)

    # Assert
    assert await conversation_service.get_partners(ALISSON) == []


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
    query: str, expected_ids: list[int], conversation_service: ConversationService
) -> None:
    """Поиск доступных пользователей фильтрует по части имени без учёта регистра"""
    # Act
    found = await conversation_service.search_available(ALISSON, query)

    # Assert
    assert [u["id"] for u in found] == expected_ids
