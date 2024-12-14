from typing import Any, Sequence

from sqlalchemy import select, or_, and_, Result, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from logger import get_logger
from src.fast_chat.dao.base import BaseDAO
from src.fast_chat.database import Base
from src.fast_chat.models.message import Message

logger = get_logger()


class MessageDAO(BaseDAO):
    model: type[Base] = Message

    @classmethod
    async def get_messages_between_users(
        cls, db_session: AsyncSession, user_id_1: int, user_id_2: int
    ):
        """
        Асинхронно находит и возвращает все сообщения между двумя пользователями.

        Аргументы:
            user_id_1: ID первого пользователя.
            user_id_2: ID второго пользователя.

        Возвращает:
            Список сообщений между двумя пользователями.
        """
        async with db_session as session:
            query = (
                select(cls.model)
                .filter(
                    or_(
                        and_(
                            cls.model.sender_id == user_id_1,
                            cls.model.recipient_id == user_id_2,
                        ),  # noqa
                        and_(
                            cls.model.sender_id == user_id_2,
                            cls.model.recipient_id == user_id_1,
                        ),  # noqa
                    )
                )
                .order_by(cls.model.id)
            )  # noqa
            query_execute: Result[tuple | Any] = await session.execute(query)
            result: Sequence[RowMapping | Any] | None = query_execute.scalars().all()
            logger.debug(f"Result: '{result}'")
            return result
