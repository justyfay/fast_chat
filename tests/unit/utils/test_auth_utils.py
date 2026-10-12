from datetime import timedelta

import pytest
from faker import Faker
from jose import jwt

from fast_chat.config import settings
from fast_chat.utils.auth import (
    create_access_token,
    get_hashed_password,
    verify_password,
)

# TO-DO: Разобраться с возможностью создавать пароли с кириллицей, пробелом и одним символом
PASSWORDS = [
    pytest.param("password", id="ascii"),
    pytest.param("P@ssw0rd!", id="special-chars"),
    pytest.param("пароль-ёЁ", id="cyrillic"),
    pytest.param(" с пробелами ", id="spaces"),
    pytest.param("a" * 200, id="long"),
]

# Пары: Верный пароль - похожий пароль
WRONG_PASSWORDS = [
    pytest.param("password", "Password", id="other-case"),
    pytest.param("password", "password ", id="trailing-space"),
    pytest.param("пароль", "Пароль", id="cyrillic-case"),
    pytest.param("P@ssw0rd!", "", id="empty"),
]


def test_hashed_password_differs_from_original(faker: Faker) -> None:
    """Хеш пароля не совпадает с исходным паролем"""
    # Arrange
    password = faker.password()

    # Act
    hashed = get_hashed_password(password)

    # Assert
    assert hashed != password


@pytest.mark.parametrize("password", PASSWORDS)
def test_verify_password_accepts_correct_password(password: str) -> None:
    """При указании правильного пароля верификация проходит"""
    # Arrange
    hashed = get_hashed_password(password)

    # Act / Assert
    assert verify_password(password, hashed)


def test_verify_password_accepts_random_password(faker: Faker) -> None:
    """При указании сгенерированного правильного пароля верификация проходит"""
    # Arrange
    password = faker.password(length=faker.random_int(min=8, max=40))
    hashed = get_hashed_password(password)

    # Act / Assert
    assert verify_password(password, hashed)


@pytest.mark.parametrize(("password", "wrong_password"), WRONG_PASSWORDS)
def test_verify_password_rejects_wrong_password(
    password: str, wrong_password: str
) -> None:
    """При указании неправильного пароля верификация не проходит"""
    # Arrange
    hashed = get_hashed_password(password)

    # Act / Assert
    assert not verify_password(wrong_password, hashed)


def test_verify_password_rejects_random_wrong_password(faker: Faker) -> None:
    """При указании сгенерированного неправильного пароля верификация не проходит"""
    # Arrange
    password = faker.password()
    wrong_password = password + faker.pystr(min_chars=1, max_chars=5)
    hashed = get_hashed_password(password)

    # Act / Assert
    assert not verify_password(wrong_password, hashed)


def test_access_token_contains_subject_and_expiration(faker: Faker) -> None:
    """JWT-токен содержит subject и срок жизни"""
    # Arrange
    subject = faker.email()

    # Act
    token = create_access_token({"sub": subject}, expires_delta=timedelta(minutes=5))

    # Assert
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == subject
    assert "exp" in payload
