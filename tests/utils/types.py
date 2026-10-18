from typing import Any, Awaitable, Callable

from .auth import UserData

# Фикстуры-функции для работы с сессией
CookiesGetter = Callable[[Any], dict]
SessionStarter = Callable[[UserData], Awaitable[dict]]
CookiesRequest = Callable[[dict], Awaitable[Any]]
