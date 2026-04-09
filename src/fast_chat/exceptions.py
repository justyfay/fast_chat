from fastapi import HTTPException
from starlette import status


class FastChatException(HTTPException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = None
    headers: dict = None

    def __init__(self) -> None:
        super().__init__(
            status_code=self.status_code, detail=self.detail, headers=self.headers
        )


class UserAlreadyExists(FastChatException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Пользователь с таким email-адресом уже существует."


class UserIncorrectCredentials(FastChatException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Неверный email или пароль."


class UserPasswordsNotEqual(FastChatException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Введенные пароли не совпадают."


class FailedDbSession(FastChatException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Не удалось получить объект сессии для работы с БД."


class TokenNoFoundException(FastChatException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Отсутствует токен пользователя."


class NoJwtException(FastChatException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Невалидный токен."


class NoFoundUserException(FastChatException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Не найден пользователь."


class TokenExpiredException(FastChatException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Токен истек."
