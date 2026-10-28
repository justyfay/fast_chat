from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fast_chat.dao.conversation import ConversationDAO
from fast_chat.dao.message import MessageDAO
from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.database import get_session, get_session_factory
from fast_chat.dependencies.redis import get_redis
from fast_chat.services.auth import AuthService
from fast_chat.services.conversation import ConversationService
from fast_chat.services.message import MessageService
from fast_chat.services.user import UserService


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserDAO(session))


def get_conversation_service(
    session: AsyncSession = Depends(get_session),
) -> ConversationService:
    return ConversationService(ConversationDAO(session), UserDAO(session))


def get_message_service(
    session: AsyncSession = Depends(get_session),
) -> MessageService:
    return MessageService(MessageDAO(session))


def get_auth_service(
    session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)
) -> AuthService:
    return AuthService(UserDAO(session), redis)


class ConnectionServices:
    """Сервисы для долгоживущего соединения, каждый вызов работает в своей сессии."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        :param session_factory: Фабрика сессий БД
        """
        self.session_factory = session_factory

    @asynccontextmanager
    async def message_service(self) -> AsyncIterator[MessageService]:
        """Сервис сообщений в одной транзакции (Коммит при выходе, откат при ошибке)."""
        async with self.session_factory() as session, session.begin():
            yield MessageService(MessageDAO(session))

    @asynccontextmanager
    async def user_service(self) -> AsyncIterator[UserService]:
        """Сервис пользователей для чтения."""
        async with self.session_factory() as session:
            yield UserService(UserDAO(session))


def get_connection_services(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> ConnectionServices:
    return ConnectionServices(session_factory)
