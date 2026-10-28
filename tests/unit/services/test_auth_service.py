from unittest.mock import AsyncMock

import pytest

from fast_chat.exceptions import UserAlreadyExists, UserPasswordsNotEqual
from fast_chat.schemas.user import UserRegisterSchema
from fast_chat.services.auth import AuthService
from fast_chat.utils.auth import verify_password

from ...constants import UsersTestData
from ...utils.auth import register_payload
from ...utils.fakes import FakeUserDAO


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(FakeUserDAO(), AsyncMock())  # type: ignore[arg-type]


async def test_register_stores_hashed_password(auth_service: AuthService) -> None:
    """При регистрации пароль сохраняется хешем, а пустой telegram-код превращается в None."""
    # Arrange
    data = UserRegisterSchema(**register_payload())

    # Act
    created = await auth_service.register(data)

    # Assert
    stored = auth_service.users.rows[0]  # type: ignore[attr-defined]
    assert created.id == stored["id"]
    assert stored["hashed_password"] != UsersTestData.DEFAULT_PASSWORD
    assert verify_password(UsersTestData.DEFAULT_PASSWORD, stored["hashed_password"])
    assert stored["telegram_unic_code"] is None


async def test_register_converts_telegram_code_to_int(
    auth_service: AuthService,
) -> None:
    """Telegram-код из формы сохраняется числом"""
    # Arrange
    data = UserRegisterSchema(**register_payload(telegram_unic_code="12345"))

    # Act
    await auth_service.register(data)

    # Assert
    assert auth_service.users.rows[0]["telegram_unic_code"] == 12345  # type: ignore[attr-defined]


async def test_error_register_existing_email(auth_service: AuthService) -> None:
    """Повторная регистрация с тем же email даёт ошибку, второй записи нет."""
    # Arrange
    data = UserRegisterSchema(**register_payload())
    await auth_service.register(data)

    # Act / Assert
    with pytest.raises(UserAlreadyExists):
        await auth_service.register(data)
    assert len(auth_service.users.rows) == 1  # type: ignore[attr-defined]


async def test_error_register_with_different_passwords(
    auth_service: AuthService,
) -> None:
    """Если пароли не совпадают, пользователь не создаётся."""
    # Arrange
    data = UserRegisterSchema(**register_payload(repeat_password="Other-P@ssw0rd!"))

    # Act / Assert
    with pytest.raises(UserPasswordsNotEqual):
        await auth_service.register(data)
    assert auth_service.users.rows == []  # type: ignore[attr-defined]
