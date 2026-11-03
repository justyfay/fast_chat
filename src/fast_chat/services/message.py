from fast_chat.dao.chat import ChatDAO
from fast_chat.dao.message import MessageDAO
from fast_chat.dao.user import UserDAO
from fast_chat.exceptions import UserNotFound
from fast_chat.schemas.message import MessageRead
from fast_chat.utils.crypto import decrypt, encrypt


class MessageService:
    """Отправка сообщений и история переписки. В БД тело сообщения хранится зашифрованным."""

    def __init__(self, messages: MessageDAO, chats: ChatDAO, users: UserDAO) -> None:
        """
        :param messages: DAO сообщений
        :param chats: DAO чатов
        :param users: DAO пользователей
        """
        self.messages = messages
        self.chats = chats
        self.users = users

    async def send(self, sender_id: int, recipient_id: int, body: str) -> MessageRead:
        """
        Сохраняет сообщение в личном чате пары и возвращает его в открытом виде.
        Чат создаётся при первом сообщении, а ушедший из него получатель возвращается в список.

        :param sender_id: Идентификатор отправителя
        :param recipient_id: Идентификатор получателя
        :param body: Текст сообщения
        """
        if not await self.users.find_one_or_none(id=recipient_id):
            raise UserNotFound
        chat_id = await self.chats.get_or_create_direct(sender_id, recipient_id)
        await self.chats.add_member(chat_id, sender_id)
        await self.chats.add_member(chat_id, recipient_id)
        created = await self.messages.add(
            chat_id=chat_id, sender_id=sender_id, body=encrypt(body)
        )
        return MessageRead(
            id=created["id"], sender_id=sender_id, recipient_id=recipient_id, body=body
        )

    async def get_history(self, user_id: int, partner_id: int) -> list[MessageRead]:
        """
        Возвращает переписку двух пользователей с расшифрованным текстом.

        :param user_id: Идентификатор текущего пользователя
        :param partner_id: Идентификатор собеседника
        """
        chat_id = await self.chats.find_direct(user_id, partner_id)
        if chat_id is None:
            return []
        return [
            MessageRead(
                id=msg.id,
                sender_id=msg.sender_id,
                recipient_id=partner_id if msg.sender_id == user_id else user_id,
                body=decrypt(msg.body),
            )
            for msg in await self.messages.get_chat_messages(chat_id)
        ]
