from fast_chat.dao.message import MessageDAO
from fast_chat.schemas.message import MessageRead
from fast_chat.utils.crypto import decrypt, encrypt


class MessageService:
    """Отправка сообщений и история переписки. В БД тело сообщения хранится зашифрованным."""

    def __init__(self, messages: MessageDAO) -> None:
        """
        :param messages: DAO сообщений
        """
        self.messages = messages

    async def send(self, sender_id: int, recipient_id: int, body: str) -> MessageRead:
        """
        Сохраняет сообщение и возвращает его в открытом виде.

        :param sender_id: Идентификатор отправителя
        :param recipient_id: Идентификатор получателя
        :param body: Текст сообщения
        """
        created = await self.messages.add(
            sender_id=sender_id, recipient_id=recipient_id, body=encrypt(body)
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
        messages = await self.messages.get_messages_between_users(user_id, partner_id)
        return [
            MessageRead(
                id=msg.id,
                sender_id=msg.sender_id,
                recipient_id=msg.recipient_id,
                body=decrypt(msg.body),
            )
            for msg in messages or []
        ]
