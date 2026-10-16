class PolicyData:
    """Константы политики требований к паролю."""

    MIN_PASSWORD_LENGTH = 8
    MIN_PASSWORD_LENGTH_DEV = 1
    MAX_PASSWORD_LENGTH = 128

    PASSWORD_TOO_SHORT_MESSAGE = "Не короче {min_length} символов"
    PASSWORD_TOO_LONG_MESSAGE = "Не длиннее {max_length} символов"
    PASSWORD_EMPTY_MESSAGE = "Пароль не может быть пустым"
    PASSWORD_COMMON_MESSAGE = "Слишком распространённый, выберите другой"
    PASSWORD_TRIVIAL_MESSAGE = "Слишком простой, выберите другой"


class AuthData:
    """Константы аутентификации."""

    # Ключ в Redis для отозванного токена (по `jti`), живёт до истечения токена
    REVOKED_TOKEN_KEY = "revoked_jti:{jti}"
