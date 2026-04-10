from typing import Sequence

from sqlalchemy import select, delete, Result
from sqlalchemy.ext.asyncio import AsyncSession

from logger import get_logger
from src.fast_chat.dao.base import BaseDAO
from src.fast_chat.database import Base
from src.fast_chat.models.conversation import Conversation
from src.fast_chat.models.user import User

logger = get_logger()


class ConversationDAO(BaseDAO):
    model: type[Base] = Conversation

    @classmethod
    async def get_partners(cls, db_session: AsyncSession, user_id: int) -> Sequence:
        """Возвращает список пользователей (User), добавленных в беседы текущим пользователем."""
        async with db_session as session:
            query = (
                select(User.__table__.columns)
                .join(Conversation, Conversation.recipient_id == User.id)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.id)
            )
            result: Result = await session.execute(query)
            rows = result.mappings().all()
            logger.debug(f"[conversation] get_partners: user_id={user_id}, count={len(rows)}")
            return rows

    @classmethod
    async def add_conversation(
        cls, db_session: AsyncSession, user_id: int, recipient_id: int
    ) -> bool:
        """Добавляет запись чата. Возвращает True если добавлено, False если уже существует."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.exc import IntegrityError

        async with db_session as session:
            try:
                stmt = (
                    pg_insert(Conversation)
                    .values(user_id=user_id, recipient_id=recipient_id)
                    .on_conflict_do_nothing(constraint="uq_conversation_pair")
                    .returning(Conversation.id)
                )
                result: Result = await session.execute(stmt)
                await session.commit()
                inserted = result.fetchone()
                logger.debug(
                    f"[conversation] add: user_id={user_id}, recipient_id={recipient_id}, inserted={inserted is not None}"
                )
                return inserted is not None
            except IntegrityError:
                await session.rollback()
                logger.warning(
                    f"[conversation] add conflict: user_id={user_id}, recipient_id={recipient_id}"
                )
                return False

    @classmethod
    async def delete_conversation(
        cls, db_session: AsyncSession, user_id: int, recipient_id: int
    ) -> bool:
        """Удаляет запись чата из списка бесед. Сообщения не затрагиваются."""
        async with db_session as session:
            stmt = delete(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.recipient_id == recipient_id,
            )
            result: Result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount > 0
            logger.debug(
                f"[conversation] delete: user_id={user_id}, recipient_id={recipient_id}, deleted={deleted}"
            )
            return deleted

    @classmethod
    async def get_available_users(cls, db_session: AsyncSession, user_id: int) -> Sequence:
        """Возвращает пользователей, с которыми у текущем пользователем ещё нет чата."""
        async with db_session as session:
            current_recipients = select(Conversation.recipient_id).where(Conversation.user_id == user_id)
            query = (
                select(User.__table__.columns)
                .where(User.id != user_id)
                .where(User.id.not_in(current_recipients))
                .order_by(User.full_name)
            )
            result: Result = await session.execute(query)
            rows = result.mappings().all()
            logger.debug(
                f"[conversation] get_available_users: user_id={user_id}, count={len(rows)}"
            )
            return rows
