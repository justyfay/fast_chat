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
