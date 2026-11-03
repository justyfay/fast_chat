from faker import Faker

import pytest

from fast_chat.exceptions import UserNotFound
from fast_chat.services.chat import ChatService
from fast_chat.services.message import MessageService
from fast_chat.utils.crypto import decrypt

from ...utils.fakes import FakeMessageDAO

ALISSON, COURTOIS = 1, 2


async def test_send_stores_encrypted_body_and_returns_plain(
    faker: Faker, message_service: MessageService, messages_dao: FakeMessageDAO
) -> None:
    """Сообщение хранится зашифрованным, а отправителю возвращается в открытом виде с id."""
    # Arrange
    body = faker.sentence()

    # Act
    sent = await message_service.send(ALISSON, COURTOIS, body)

    # Assert
    assert (sent.sender_id, sent.recipient_id, sent.body) == (ALISSON, COURTOIS, body)
    stored = messages_dao.rows[0]
    assert sent.id == stored.id
    assert stored.body != body
    assert decrypt(stored.body) == body


async def test_history_returns_decrypted_dialog_only(
    message_service: MessageService,
) -> None:
    """История содержит расшифрованную переписку двух пользователей и не содержит чужих сообщений."""
    # Arrange
    await message_service.send(ALISSON, COURTOIS, "hello")
    await message_service.send(COURTOIS, ALISSON, "hi")
    await message_service.send(ALISSON, 3, "other")

    # Act
    history = await message_service.get_history(ALISSON, COURTOIS)

    # Assert
    assert [m.body for m in history] == ["hello", "hi"]


async def test_error_send_to_unknown_user(
    message_service: MessageService, messages_dao: FakeMessageDAO
) -> None:
    """Сообщение несуществующему пользователю не сохраняется."""
    # Act / Assert
    with pytest.raises(UserNotFound):
        await message_service.send(ALISSON, 99, "привет")
    assert messages_dao.rows == []


async def test_first_message_creates_chat_visible_to_both(
    message_service: MessageService, chat_service: ChatService
) -> None:
    """Первое сообщение создаёт личный чат, который виден обоим участникам."""
    # Act
    await message_service.send(ALISSON, COURTOIS, "привет")

    # Assert
    assert [p["id"] for p in await chat_service.get_partners(ALISSON)] == [COURTOIS]
    assert [p["id"] for p in await chat_service.get_partners(COURTOIS)] == [ALISSON]


async def test_new_message_returns_removed_chat_to_list(
    message_service: MessageService, chat_service: ChatService
) -> None:
    """Новое сообщение возвращает в список чат, который получатель ранее убрал."""
    # Arrange
    await message_service.send(ALISSON, COURTOIS, "Hello!")
    await chat_service.delete(COURTOIS, ALISSON)

    # Act
    await message_service.send(ALISSON, COURTOIS, "You are here?")

    # Assert
    assert [p["id"] for p in await chat_service.get_partners(COURTOIS)] == [ALISSON]


async def test_history_of_pair_without_chat_is_empty(
    message_service: MessageService,
) -> None:
    """У пользователей без общего чата история пуста."""
    # Act / Assert
    assert await message_service.get_history(ALISSON, COURTOIS) == []
