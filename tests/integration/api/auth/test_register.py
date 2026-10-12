from async_asgi_testclient import TestClient
from asyncpg import Connection
from fastapi import status

from fast_chat.utils.auth import verify_password
from ....constants import RoutersTestData, UsersTestData
from ....utils.auth import register_payload


async def test_register_success_creates_user(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Регистрация нового пользователя создаёт запись в БД"""
    # Arrange
    payload = register_payload(email="alisson@example.com", full_name="Alisson Becker")

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["email"] == "alisson@example.com"
    assert body["username"] == "alisson@example.com"
    assert body["full_name"] == "Alisson Becker"
    row = await pg_conn.fetchrow('SELECT * FROM "user" WHERE id = $1', body["id"])
    assert row["email"] == "alisson@example.com"
    assert row["telegram_unic_code"] is None


async def test_register_stores_password_as_hash(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Пароль при регистрации сохраняется в виде хеша"""
    # Arrange
    payload = register_payload()

    # Act
    await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    row = await pg_conn.fetchrow('SELECT hashed_password FROM "user"')
    assert row["hashed_password"] != UsersTestData.DEFAULT_PASSWORD
    assert verify_password(UsersTestData.DEFAULT_PASSWORD, row["hashed_password"])


async def test_register_saves_telegram_code_as_int(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Telegram-код при регистрации сохраняется как число"""
    # Arrange
    payload = register_payload(telegram_unic_code="123456")

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    row = await pg_conn.fetchrow('SELECT telegram_unic_code FROM "user"')
    assert row["telegram_unic_code"] == 123456


async def test_error_register_duplicate_email(
    main_client: TestClient,
) -> None:
    """Повторная регистрация с существующим email невозможна"""
    # Arrange
    payload = register_payload()
    await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_409_CONFLICT


async def test_error_register_different_passwords(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """При несовпадении паролей при регистрации возвращается ошибка"""
    # Arrange
    payload = register_payload(repeat_password="another-password")

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0


async def test_validation_error_register_invalid_email(
    main_client: TestClient,
) -> None:
    """Регистрация с некорректным email приводит к ошибке валидации"""
    # Arrange
    payload = register_payload(email="not-an-email")

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
