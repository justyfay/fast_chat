from faker import Faker

from fast_chat.services.message import MessageService
from fast_chat.utils.crypto import decrypt

from ...utils.fakes import FakeMessageDAO

ALISSON, COURTOIS = 1, 2


async def test_send_stores_encrypted_body_and_returns_plain(
    faker: Faker, message_service: MessageService, messages_dao: FakeMessageDAO
) -> None:
    """Сообщение хранится зашифрованным, а отправителю возвращается в открытом виде с id"""
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
    """История содержит расшифрованную переписку двух пользователей и не содержит чужих сообщений"""
    # Arrange
    await message_service.send(ALISSON, COURTOIS, "hello")
    await message_service.send(COURTOIS, ALISSON, "hi")
    await message_service.send(ALISSON, 3, "other")

    # Act
    history = await message_service.get_history(ALISSON, COURTOIS)

    # Assert
    assert [m.body for m in history] == ["hello", "hi"]
