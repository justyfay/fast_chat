from typing import Any, Sequence

from sqlalchemy import select, or_, and_, Result, RowMapping

from fast_chat.logger import get_logger
from fast_chat.dao.base import BaseDAO
from fast_chat.database import Base
from fast_chat.models.message import Message

logger = get_logger()


class MessageDAO(BaseDAO):
    model: type[Base] = Message
    filterable_fields = frozenset({"id"})

    async def get_messages_between_users(self, user_id_1: int, user_id_2: int):
        """
        Асинхронно находит и возвращает все сообщения между двумя пользователями.

        Аргументы:
            user_id_1: ID первого пользователя.
            user_id_2: ID второго пользователя.

        Возвращает:
            Список сообщений между двумя пользователями.
        """
        query = (
            select(self.model)
            .filter(
                or_(
                    and_(
                        self.model.sender_id == user_id_1,
                        self.model.recipient_id == user_id_2,
                    ),  # noqa
                    and_(
                        self.model.sender_id == user_id_2,
                        self.model.recipient_id == user_id_1,
                    ),  # noqa
                )
            )
            .order_by(self.model.id)
        )  # noqa
        query_execute: Result[tuple | Any] = await self.session.execute(query)
        result: Sequence[RowMapping | Any] | None = query_execute.scalars().all()
        logger.debug(
            f"[message] get_messages_between_users: count={len(result) if result else 0}"
        )
        return result
