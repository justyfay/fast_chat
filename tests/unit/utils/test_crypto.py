import pytest
from faker import Faker

from fast_chat.utils.crypto import decrypt, encrypt

TEXTS = [
    pytest.param("secret message", id="ascii"),
    pytest.param("Привет, мир!", id="cyrillic"),
    pytest.param("😀 🔑", id="emoji"),
    pytest.param("line1\nline2\ttab", id="whitespace"),
    pytest.param("a" * 10_000, id="long"),
    pytest.param("", id="empty"),
]


@pytest.mark.parametrize("text", TEXTS)
def test_encrypt_returns_different_text(text: str) -> None:
    """Зашифрованный текст отличается от исходного"""
    # Act
    token = encrypt(text)

    # Assert
    assert token != text


@pytest.mark.parametrize("text", TEXTS)
def test_decrypt_restores_original_text(text: str) -> None:
    """Расшифровка возвращает исходный текст"""
    # Arrange
    token = encrypt(text)

    # Act
    result = decrypt(token)

    # Assert
    assert result == text


def test_decrypt_restores_random_text(faker: Faker) -> None:
    """Расшифровка возвращает исходный случайный текст"""
    # Arrange
    text = faker.text(max_nb_chars=500)
    token = encrypt(text)

    # Act
    result = decrypt(token)

    # Assert
    assert result == text


def test_encrypt_is_not_deterministic(faker: Faker) -> None:
    """Шифрование одного и того же текста каждый раз даёт разный результат"""
    # Arrange
    text = faker.sentence()

    # Act
    first, second = encrypt(text), encrypt(text)

    # Assert
    assert first != second


def test_decrypt_returns_plain_text_as_is(faker: Faker) -> None:
    """Расшифровка незашифрованного текста возвращает исходный текст"""
    # TO-DO: Поправить после удаления fallback для незашифрованных сообщений
    # Arrange
    text = faker.sentence()

    # Act
    result = decrypt(text)

    # Assert
    assert result == text
