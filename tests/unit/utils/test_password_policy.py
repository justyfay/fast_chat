import pytest

from fast_chat.constants import PolicyData
from fast_chat.utils.password_policy import (
    is_common_password,
    load_common_passwords,
    password_base,
    validate_password,
)

from ...constants import PasswordTestData


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("kd9Lm2xq", id="min-length"),
        pytest.param("пароль-из-кириллицы", id="cyrillic"),
        pytest.param("correct horse battery staple", id="spaces"),
        pytest.param(
            "😀" * PolicyData.MIN_PASSWORD_LENGTH, id="emoji-counted-as-characters"
        ),
        pytest.param("Tr0ub4dor&3", id="symbols"),
        pytest.param("я" * PolicyData.MAX_PASSWORD_LENGTH, id="max-length"),
    ],
)
def test_strict_accepts_valid_password(password: str) -> None:
    """Строгий режим валидации принимает пароли от
    8 символов со знаками и пробелами."""
    # Act
    problems = validate_password(password, strict=True)

    # Assert
    assert problems == []


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("", id="empty"),
        pytest.param("a", id="one-char"),
        pytest.param(PasswordTestData.SHORT, id="one-char-less-than-min"),
        pytest.param(
            "я" * (PolicyData.MIN_PASSWORD_LENGTH - 1), id="cyrillic-less-than-min"
        ),
    ],
)
def test_strict_rejects_too_short_password(password: str) -> None:
    """Строгий режим валидации отклоняет пароль меньше 8 символов."""
    # Act
    problems = validate_password(password, strict=True)

    # Assert
    assert problems == [PasswordTestData.TOO_SHORT_MESSAGE]


def test_strict_rejects_too_long_password() -> None:
    """Строгий режим валидации отклоняет пароль больше 128 символов."""
    # Act
    problems = validate_password(
        "я" * (PolicyData.MAX_PASSWORD_LENGTH + 1), strict=True
    )

    # Assert
    assert problems == [PasswordTestData.TOO_LONG_MESSAGE]


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("password", id="whole"),
        pytest.param("12345678", id="digits"),
        pytest.param("PASSWORD", id="uppercase"),
        pytest.param("Password1", id="capital-and-digit"),
        pytest.param(PasswordTestData.COMMON, id="capital-digit-symbol"),
        pytest.param("!!qwerty123!!", id="symbols-around"),
        pytest.param("12password34", id="digits-around"),
        pytest.param(" password ", id="spaces-around"),
    ],
)
def test_strict_rejects_common_password(password: str) -> None:
    """Строгий режим валидации отклоняет распространённый пароль,
    в том числе с цифрами и знаками на границах."""
    # Act
    problems = validate_password(password, strict=True)

    # Assert
    assert problems == [PolicyData.PASSWORD_COMMON_MESSAGE]


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        pytest.param("Password1!", "password", id="digit-and-symbol"),
        pytest.param("  ab-cd  ", "ab-cd", id="inner-symbols-are-kept"),
        pytest.param("Привет1", "привет", id="cyrillic"),
        pytest.param("12345678", "", id="no-letters"),
    ],
)
def test_password_base_strips_non_letters_around(password: str, expected: str) -> None:
    """Отсечение символов по краям для проверки паролей."""
    # Act
    base = password_base(password)

    # Assert
    assert base == expected


def test_password_without_letters_is_checked_as_a_whole() -> None:
    """Пароль без букв сверяется со списком целиком."""
    # Act / Assert
    assert is_common_password("12345678")
    assert not is_common_password("83746592")


def test_common_passwords_list_is_loaded() -> None:
    """Загрузка списка распространённых паролей, значения приведены к нижнему регистру."""
    # Act
    common = load_common_passwords()

    # Assert
    assert len(common) > 9000
    assert "password" in common
    assert all(item == item.casefold() for item in common)
