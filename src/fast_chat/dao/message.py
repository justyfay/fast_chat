from typing import Sequence

from sqlalchemy import select

from fast_chat.logger import get_logger
from fast_chat.dao.base import BaseDAO
from fast_chat.database import Base
from fast_chat.models.message import Message

logger = get_logger()


class MessageDAO(BaseDAO):
    model: type[Base] = Message
    filterable_fields = frozenset({"id"})

    async def get_chat_messages(self, chat_id: int) -> Sequence[Message]:
        """
        Возвращает все сообщения чата по возрастанию id.

        :param chat_id: Идентификатор чата
        """
        query = (
            select(self.model)
            .where(self.model.chat_id == chat_id)
            .order_by(self.model.id)
        )
        result: Sequence[Message] = (await self.session.execute(query)).scalars().all()
        logger.debug(
            f"[message] get_chat_messages: chat_id={chat_id}, count={len(result)}"
        )
        return result
