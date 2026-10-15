class RoutersTestData:
    """URL's эндпоинтов приложения."""

    # Авторизация
    REGISTER_URL = "/v1/auth/register"
    LOGIN_URL = "/v1/auth/login"
    LOGOUT_URL = "/v1/auth/logout"

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
