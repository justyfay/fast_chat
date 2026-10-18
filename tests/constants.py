from fast_chat.config import settings
from fast_chat.constants import PolicyData


class RoutersTestData:
    """URL's эндпоинтов приложения."""

    # Авторизация
    REGISTER_URL = "/v1/auth/register"
    LOGIN_URL = "/v1/auth/login"
    LOGOUT_URL = "/v1/auth/logout"
    REFRESH_URL = "/v1/auth/refresh"

    # Пользователи
    CURRENT_USER_URL = "/v1/users/current_user"
    ALL_USERS_URL = "/v1/users/all"

    # Беседы
    CONVERSATIONS_URL = "/v1/conversations/"
    CONVERSATIONS_SEARCH_URL = "/v1/conversations/search"

    # Сообщения
    MESSAGES_SEND_URL = "/v1/messages/send"
    MESSAGES_URL = "/v1/messages/{user_id}"

    # WebSocket
    WS_URL = "/v1/ws/{user_id}"

    # Страницы
    CHAT_PAGE_URL = "/"
    LOGIN_PAGE_URL = "/login"


class UsersTestData:
    """Общие тестовые данные пользователей."""

    DEFAULT_PASSWORD = "P@ssw0rd!"


class ComposeTestData:
    """Тестовые данные для проверки docker-compose.yml."""

    # Тестовые секреты в `.env` временного каталога
    ENV = {
        "DB_USER": "test_user",
        "DB_PASS": "test-db-pass",
        "DB_NAME": "test_db",
        "DB_PORT": "5432",
        "REDIS_PASSWORD": "test-redis-pass",
        "FLOWER_BASIC_AUTH": "test-user:test-flower-pass",
        "PGADMIN_DEFAULT_EMAIL": "test@example.com",
        "PGADMIN_DEFAULT_PASSWORD": "test-pgadmin-pass",
    }
    # Сервисы, порты которых должны быть доступны только с самого хоста
    LOCAL_ONLY_SERVICES = ("postgres", "redis", "flower", "pgadmin")
    # Обязательные переменные compose
    REQUIRED_VARIABLES = (
        "DB_PASS",
        "REDIS_PASSWORD",
        "FLOWER_BASIC_AUTH",
        "PGADMIN_DEFAULT_EMAIL",
        "PGADMIN_DEFAULT_PASSWORD",
    )


class RateLimitTestData:
    """Тестовые данные для проверки ограничения частоты запросов."""

    LIMITER_NAME = "unit"
    ATTEMPTS = 3
    INTERVAL_SECONDS = 30
    AUTH_ATTEMPTS = settings.rate_limit_auth_attempts
    AUTH_INTERVAL_SECONDS = settings.rate_limit_auth_seconds
    CLIENT_PORT = 50000
    FIRST_IP = "10.0.0.1"
    SECOND_IP = "10.0.0.2"
    UNKNOWN_EMAIL = "nobody@example.com"


class XssTestData:
    """Тестовые данные для проверки защиты от XSS."""

    PAYLOAD = "<img src=x onerror=alert(1)>"
    EMAIL = "mallory@example.com"
    LIBS_SCRIPTS = (
        "/static/js/libs/marked.umd.js",
        "/static/js/libs/purify.js",
    )


class PasswordTestData:
    """Тестовые данные для проверки политики паролей."""

    SHORT = "1" * (PolicyData.MIN_PASSWORD_LENGTH - 1)
    TOO_SHORT_MESSAGE = PolicyData.PASSWORD_TOO_SHORT_MESSAGE.format(
        min_length=PolicyData.MIN_PASSWORD_LENGTH
    )
    TOO_LONG_MESSAGE = PolicyData.PASSWORD_TOO_LONG_MESSAGE.format(
        max_length=PolicyData.MAX_PASSWORD_LENGTH
    )
    COMMON = "Password1!"
    CYRILLIC_PASSPHRASE = "длинная парольная фраза"
    ONE_CHAR = "a"


class TokenTestData:
    """Тестовые данные для проверки токенов."""

    SUBJECT = "nobody@example.com"
    GARBAGE_TOKEN = "not-a-jwt"
    REVOKED_MESSAGE = "Токен отозван"
    EXPIRED_MESSAGE = "Токен истек"
    USED_LONG_AGO_SECONDS = 100
