from async_asgi_testclient import TestClient
from asyncpg import Connection
from faker import Faker
from fastapi import status

from fast_chat.utils.crypto import decrypt
from ....constants import RoutersTestData
from ....utils.auth import UserData


async def test_send_message_saves_encrypted_body(
    main_client: TestClient,
    pg_conn: Connection,
    user_one: UserData,
    user_two: UserData,
    faker: Faker,
) -> None:
    """Отправленное сообщение сохраняется в БД в зашифрованном виде"""
    # Arrange
    payload = {"recipient_id": user_two.id, "body": faker.sentence()}

    # Act
    resp = await main_client.post(RoutersTestData.MESSAGES_SEND_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == payload
    row = await pg_conn.fetchrow("SELECT * FROM message")
    assert row["sender_id"] == user_one.id
    assert row["recipient_id"] == user_two.id
    assert row["body"] != payload["body"]
    assert decrypt(row["body"]) == payload["body"]


async def test_get_messages_returns_dialog_in_order_for_both_sides(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
) -> None:
    """История диалога возвращается в хронологическом порядке,
    который одинаков для обоих участников"""
    # Arrange
    await main_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_two.id, "body": "one"},
    )
    await other_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_one.id, "body": "two"},
    )
    await main_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_two.id, "body": "three"},
    )

    # Act
    user_one_view = await main_client.get(
        RoutersTestData.MESSAGES_URL.format(user_id=user_two.id)
    )
    user_two_view = await other_client.get(
        RoutersTestData.MESSAGES_URL.format(user_id=user_one.id)
    )

    # Assert
    assert user_one_view.status_code == status.HTTP_200_OK
    assert [(m["sender_id"], m["body"]) for m in user_one_view.json()] == [
        (user_one.id, "one"),
        (user_two.id, "two"),
        (user_one.id, "three"),
    ]
    assert user_one_view.json() == user_two_view.json()


async def test_get_messages_does_not_include_other_dialogs(
    main_client: TestClient,
    other_client: TestClient,
    user_one: UserData,
    user_two: UserData,
    faker: Faker,
) -> None:
    """История диалога не включает сообщения других диалогов"""
    # Arrange
    await main_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_two.id, "body": faker.sentence()},
    )

    # Act
    resp = await main_client.get(RoutersTestData.MESSAGES_URL.format(user_id=999999))

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


async def test_get_messages_returns_all_fields(
    main_client: TestClient, user_one: UserData, user_two: UserData, faker: Faker
) -> None:
    """История диалога содержит id, отправителя, получателя и текст сообщения"""
    # Arrange
    body = faker.sentence()
    await main_client.post(
        RoutersTestData.MESSAGES_SEND_URL,
        json={"recipient_id": user_two.id, "body": body},
    )

    # Act
    resp = await main_client.get(
        RoutersTestData.MESSAGES_URL.format(user_id=user_two.id)
    )

    # Assert
    assert resp.json() == [
        {
            "id": resp.json()[0]["id"],
            "sender_id": user_one.id,
            "recipient_id": user_two.id,
            "body": body,
        }
    ]


async def test_messages_without_cookie_redirect_to_login(
    main_client: TestClient,
) -> None:
    """Неавторизованный запрос истории сообщений перенаправляет на страницу входа"""
    # Act
    resp = await main_client.get(
        RoutersTestData.MESSAGES_URL.format(user_id=1), allow_redirects=False
    )

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL
