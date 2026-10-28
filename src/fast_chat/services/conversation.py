from typing import Sequence

from sqlalchemy import RowMapping

from fast_chat.dao.conversation import ConversationDAO
from fast_chat.dao.user import UserDAO
from fast_chat.exceptions import CannotAddYourself, ConversationNotFound, UserNotFound


class ConversationService:
    """Список бесед пользователя."""

    def __init__(self, conversations: ConversationDAO, users: UserDAO) -> None:
        """
        :param conversations: DAO бесед
        :param users: DAO пользователей
        """
        self.conversations = conversations
        self.users = users

    async def get_partners(self, user_id: int) -> Sequence[RowMapping]:
        """
        Возвращает собеседников, добавленных пользователем в беседы.

        :param user_id: Идентификатор текущего пользователя
        """
        return await self.conversations.get_partners(user_id)

    async def add(self, user_id: int, recipient_id: int) -> bool:
        """
        Добавляет собеседника в список бесед. Возвращает False, если он уже добавлен.

        :param user_id: Идентификатор текущего пользователя
        :param recipient_id: Идентификатор добавляемого собеседника
        """
        if recipient_id == user_id:
            raise CannotAddYourself
        if not await self.users.find_one_or_none(id=recipient_id):
            raise UserNotFound
        return await self.conversations.add_conversation(user_id, recipient_id)

    async def delete(self, user_id: int, recipient_id: int) -> None:
        """
        Удаляет собеседника из списка бесед, сообщения сохраняются.

        :param user_id: Идентификатор текущего пользователя
        :param recipient_id: Идентификатор удаляемого собеседника
        """
        if not await self.conversations.delete_conversation(user_id, recipient_id):
            raise ConversationNotFound

    async def search_available(self, user_id: int, query: str) -> Sequence[RowMapping]:
        """
        Возвращает пользователей, которых можно добавить в беседы, с фильтром по имени.

        :param user_id: Идентификатор текущего пользователя.
        :param query: Часть имени пользователя без учёта регистра.
        """
        users = await self.conversations.get_available_users(user_id)
        if query:
            query_lower = query.lower()
            users = [u for u in users if query_lower in u["full_name"].lower()]
        return users
