from functools import lru_cache
from pathlib import Path

from fast_chat.constants import PolicyData

COMMON_PASSWORDS_FILE = (
    Path(__file__).resolve().parent.parent / "blocklists" / "common_passwords.txt"
)


@lru_cache(maxsize=1)
def load_common_passwords() -> frozenset[str]:
    """Список распространённых паролей: читается один раз, значения приведены к нижнему регистру."""
    with COMMON_PASSWORDS_FILE.open(encoding="utf-8") as file:
        return frozenset(line.strip().casefold() for line in file if line.strip())


def password_base(password: str) -> str:
    """Метод отсекает у пароля символы по краям,
    которые не являются буквами, для определения «слабости» пароля.

    Например: `Password1!` -> `password`.
    """
    folded = password.casefold()
    letters = [index for index, char in enumerate(folded) if char.isalpha()]
    if not letters:
        return ""
    return folded[letters[0] : letters[-1] + 1]


def is_common_password(password: str) -> bool:
    """Проверяет пароль на наличие в списке распространённых
    целиком и после удаления символов по краям."""
    common = load_common_passwords()
    if password.casefold() in common:
        return True
    base = password_base(password)
    return bool(base) and base in common


def validate_password(password: str, strict: bool) -> list[str]:
    """Метод возвращает список нарушенных правил валидации (пустой, если пароль подходит)."""
    messages = []
    min_length = (
        PolicyData.MIN_PASSWORD_LENGTH if strict else PolicyData.MIN_PASSWORD_LENGTH_DEV
    )
    if len(password) < min_length:
        if strict:
            messages.append(
                PolicyData.PASSWORD_TOO_SHORT_MESSAGE.format(min_length=min_length)
            )
        else:
            messages.append(PolicyData.PASSWORD_EMPTY_MESSAGE)
    if len(password) > PolicyData.MAX_PASSWORD_LENGTH:
        messages.append(
            PolicyData.PASSWORD_TOO_LONG_MESSAGE.format(
                max_length=PolicyData.MAX_PASSWORD_LENGTH
            )
        )
    if strict and not messages and is_common_password(password):
        messages.append(PolicyData.PASSWORD_COMMON_MESSAGE)
    return messages
