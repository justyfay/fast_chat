from typing import Sequence

from sqlalchemy import RowMapping

from fast_chat.dao.chat import ChatDAO
from fast_chat.dao.user import UserDAO
from fast_chat.exceptions import CannotAddYourself, ConversationNotFound, UserNotFound


class ChatService:
    """Личные чаты пользователя. Личный чат общий, после добавления
    он виден обоим участникам."""

    def __init__(self, chats: ChatDAO, users: UserDAO) -> None:
        """
        :param chats: DAO чатов
        :param users: DAO пользователей
        """
        self.chats = chats
        self.users = users

    async def get_partners(self, user_id: int) -> Sequence[RowMapping]:
        """
        Возвращает собеседников из личных чатов пользователя.

        :param user_id: Идентификатор текущего пользователя
        """
        return await self.chats.get_partners(user_id)

    async def add(self, user_id: int, recipient_id: int) -> bool:
        """
        Создаёт личный чат с пользователем (если его ещё нет) и добавляет в него обоих.
        Возвращает False, если чат уже был в списке пользователя.

        :param user_id: Идентификатор текущего пользователя
        :param recipient_id: Идентификатор добавляемого собеседника
        """
        if recipient_id == user_id:
            raise CannotAddYourself
        if not await self.users.find_one_or_none(id=recipient_id):
            raise UserNotFound
        chat_id = await self.chats.get_or_create_direct(user_id, recipient_id)
        await self.chats.add_member(chat_id, recipient_id)
        return await self.chats.add_member(chat_id, user_id)

    async def delete(self, user_id: int, recipient_id: int) -> None:
        """
        Убирает чат из списка пользователя. Сообщения и чат у собеседника остаются,
        новое сообщение возвращает чат в список.

        :param user_id: Идентификатор текущего пользователя
        :param recipient_id: Идентификатор собеседника
        """
        chat_id = await self.chats.find_direct(user_id, recipient_id)
        if chat_id is None or not await self.chats.remove_member(chat_id, user_id):
            raise ConversationNotFound

    async def search_available(self, user_id: int, query: str) -> Sequence[RowMapping]:
        """
        Возвращает пользователей, которых можно добавить в чаты. Из них вернутся те, у кого
        строка поиска входит в имя (`full_name`) в любом месте и в любом регистре.

        :param user_id: Идентификатор текущего пользователя
        :param query: Строка поиска, пустая строка - без фильтра
        """
        users = await self.chats.get_available_users(user_id)
        if query:
            query_lower = query.lower()
            users = [u for u in users if query_lower in u["full_name"].lower()]
        return users
