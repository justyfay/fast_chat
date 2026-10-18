class PolicyData:
    """Константы политики требований к паролю."""

    MIN_PASSWORD_LENGTH = 8
    MIN_PASSWORD_LENGTH_DEV = 1
    MAX_PASSWORD_LENGTH = 128

    PASSWORD_TOO_SHORT_MESSAGE = "Не короче {min_length} символов"
    PASSWORD_TOO_LONG_MESSAGE = "Не длиннее {max_length} символов"
    PASSWORD_EMPTY_MESSAGE = "Пароль не может быть пустым"
    PASSWORD_COMMON_MESSAGE = "Слишком распространённый, выберите другой"


class AuthData:
    """Константы аутентификации."""

    REVOKED_TOKEN_KEY = "revoked_jti:{jti}"
    REVOKED_SESSION_KEY = "revoked_sid:{sid}"
    REFRESH_TOKEN_KEY = "refresh:{token_hash}"
    REFRESH_USED_KEY = "refresh_used:{token_hash}"
    SESSION_REFRESH_KEY = "session_refresh:{sid}"
    REFRESH_COOKIE = "refresh_token"
    REFRESH_COOKIE_PATH = "/v1/auth"
    REFRESH_GRACE_SECONDS = 10
