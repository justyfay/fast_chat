from async_asgi_testclient import TestClient
from asyncpg import Connection
from fastapi import status
from pytest_mock import MockerFixture

from fast_chat.config import settings
from fast_chat.constants import PolicyData
from fast_chat.utils.auth import verify_password
from ....constants import PasswordTestData, RoutersTestData, UsersTestData
from ....utils.auth import login_user, register_payload


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


async def test_error_register_with_short_password(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Невозможно зарегестрировваться с паролем меньше 8 символов."""
    # Arrange
    payload = register_payload(password=PasswordTestData.SHORT)

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert PasswordTestData.TOO_SHORT_MESSAGE in resp.json()["detail"][0]["msg"]
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0


async def test_error_register_with_common_password(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Невозможно зарегестрировваться с распространенным паролем."""
    # Arrange
    payload = register_payload(password=PasswordTestData.COMMON)

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert PolicyData.PASSWORD_COMMON_MESSAGE in resp.json()["detail"][0]["msg"]
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0


async def test_error_register_with_trivial_password(
    main_client: TestClient, pg_conn: Connection
) -> None:
    """Ошибка при регистрации пользователя с тривиальным паролем."""
    # Arrange
    payload = register_payload(password=PasswordTestData.TRIVIAL)

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert PolicyData.PASSWORD_TRIVIAL_MESSAGE in resp.json()["detail"][0]["msg"]
    assert await pg_conn.fetchval('SELECT count(*) FROM "user"') == 0


async def test_register_accepts_cyrillic_passphrase_with_spaces(
    main_client: TestClient,
) -> None:
    """Возможно зарегестрировваться с паролем из кириллицы и пробелов."""
    # Arrange
    payload = register_payload(password=PasswordTestData.CYRILLIC_PASSPHRASE)

    # Act
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)

    # Assert
    assert resp.status_code == status.HTTP_200_OK


async def test_login_is_not_checked_against_password_policy(
    main_client: TestClient, mocker: MockerFixture
) -> None:
    """Ранее созданный пользователь со 'слабым' паролем может авторизоваться."""
    # Arrange
    mocker.patch.object(settings, "password_policy_strict", False)
    payload = register_payload(password=PasswordTestData.ONE_CHAR)
    resp = await main_client.post(RoutersTestData.REGISTER_URL, json=payload)
    assert resp.status_code == status.HTTP_200_OK
    mocker.patch.object(settings, "password_policy_strict", True)

    # Act / Assert
    await login_user(main_client, payload["email"], PasswordTestData.ONE_CHAR)
