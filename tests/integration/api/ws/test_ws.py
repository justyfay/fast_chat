import pytest
from async_asgi_testclient import TestClient
from asyncpg import Connection
from faker import Faker
from pytest_mock import MockerFixture

from ....constants import RoutersTestData
from ....utils.auth import UserData, register_payload
from ....utils.ws import receive_json


@pytest.fixture
def telegram_task(mocker: MockerFixture):
    return mocker.patch("fast_chat.routers.v1.ws.send_notification_to_telegram")


async def test_message_is_delivered_to_online_recipient_and_echoed_to_sender(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """
    Обмен сообщениями между двумя пользователями:
    получатель получает сообщение, отправителю приходит копия
    """
    # Arrange
    body = faker.sentence()
    async with (
        main_client.websocket_connect(
            RoutersTestData.WS_URL.format(user_id=user_one.id)
        ) as alisson_ws,
        other_client.websocket_connect(
            RoutersTestData.WS_URL.format(user_id=user_two.id)
        ) as courtois_ws,
    ):
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_one.id, "recipient_id": user_two.id, "body": body}
        )
        courtois_msg = await receive_json(courtois_ws)
        alisson_msg = await receive_json(alisson_ws)

    # Assert
    assert courtois_msg == alisson_msg
    assert courtois_msg["sender_id"] == user_one.id
    assert courtois_msg["recipient_id"] == user_two.id
    assert courtois_msg["body"] == body
    telegram_task.delay.assert_not_called()


async def test_message_is_saved_and_available_via_history(
    main_client: TestClient,
    user_one: UserData,
    user_two: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """Сообщение, отправленное через WebSocket, сохраняется и доступно в истории"""
    # Arrange
    body = faker.sentence()
    async with main_client.websocket_connect(
        RoutersTestData.WS_URL.format(user_id=user_one.id)
    ) as alisson_ws:
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_one.id, "recipient_id": user_two.id, "body": body}
        )
        await receive_json(alisson_ws)

    # Assert
    history = (
        await main_client.get(RoutersTestData.MESSAGES_URL.format(user_id=user_two.id))
    ).json()
    assert [(m["sender_id"], m["body"]) for m in history] == [(user_one.id, body)]


async def test_message_body_is_encrypted_in_db(
    main_client: TestClient,
    pg_conn: Connection,
    user_one: UserData,
    user_two: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """Сообщение, отправленное через WebSocket, хранится в БД в зашифрованном виде"""
    # Arrange
    body = faker.sentence()
    async with main_client.websocket_connect(
        RoutersTestData.WS_URL.format(user_id=user_one.id)
    ) as alisson_ws:
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_one.id, "recipient_id": user_two.id, "body": body}
        )
        await receive_json(alisson_ws)

    # Assert
    assert await pg_conn.fetchval("SELECT body FROM message") != body


async def test_offline_recipient_with_telegram_code_gets_notification(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """Оффлайн-получателю с Telegram-кодом отправляется уведомление в Telegram"""
    # Arrange
    body = faker.sentence()
    user_two = await other_client.post(
        RoutersTestData.REGISTER_URL,
        json=register_payload(
            email="courtois@example.com",
            full_name="Thibaut Courtois",
            telegram_unic_code="777",
        ),
    )
    user_two_id = user_two.json()["id"]

    async with main_client.websocket_connect(
        RoutersTestData.WS_URL.format(user_id=user_one.id)
    ) as alisson_ws:
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_one.id, "recipient_id": user_two_id, "body": body}
        )
        await receive_json(alisson_ws)

    # Assert
    telegram_task.delay.assert_called_once_with(
        chat_id=777, message=body, sender_name="Alisson Becker"
    )


async def test_offline_recipient_without_telegram_code_gets_no_notification(
    main_client: TestClient,
    user_one: UserData,
    user_two: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """Оффлайн-получателю без Telegram-кода уведомление не отправляется"""
    # Arrange
    body = faker.sentence()
    async with main_client.websocket_connect(
        RoutersTestData.WS_URL.format(user_id=user_one.id)
    ) as alisson_ws:
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_one.id, "recipient_id": user_two.id, "body": body}
        )
        await receive_json(alisson_ws)

    # Assert
    telegram_task.delay.assert_not_called()


@pytest.mark.xfail(
    strict=True,
    reason="TO-DO: Поправить после добавления проверки cookie при подключении к WebSocket",
)
async def test_connection_without_cookie_is_rejected(
    main_client: TestClient, user_one: UserData
) -> None:
    """Подключение к WebSocket без cookie отклоняется"""
    # Arrange
    anonymous_client = TestClient(main_client.application)

    # Act / Assert
    with pytest.raises(AssertionError):
        async with anonymous_client.websocket_connect(
            RoutersTestData.WS_URL.format(user_id=user_one.id)
        ):
            pass


@pytest.mark.xfail(
    strict=True,
    reason="TO-DO: Поправить после того, как отправитель начнёт определяться по токену",
)
async def test_sender_id_from_payload_is_ignored(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
    telegram_task,
    faker: Faker,
) -> None:
    """Отправитель определяется по токену, а sender_id из сообщения игнорируется"""
    # Arrange: user_one (Alisson) подключен под своим токеном,
    # но подписывается как user_two (Courtois)
    body = faker.sentence()
    async with main_client.websocket_connect(
        RoutersTestData.WS_URL.format(user_id=user_one.id)
    ) as alisson_ws:
        # Act
        await alisson_ws.send_json(
            {"sender_id": user_two.id, "recipient_id": user_one.id, "body": body}
        )
        message = await receive_json(alisson_ws)

    # Assert
    assert message["sender_id"] == user_one.id
