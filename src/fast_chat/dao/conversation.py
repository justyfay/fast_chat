from typing import Sequence

from sqlalchemy import select, delete, Result
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fast_chat.logger import get_logger
from fast_chat.dao.base import BaseDAO
from fast_chat.database import Base
from fast_chat.models.conversation import Conversation
from fast_chat.models.user import User

logger = get_logger()


class ConversationDAO(BaseDAO):
    model: type[Base] = Conversation

    async def get_partners(self, user_id: int) -> Sequence:
        """Возвращает список пользователей (User), добавленных в беседы текущим пользователем."""
        query = (
            select(User.__table__.columns)
            .join(Conversation, Conversation.recipient_id == User.id)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.id)
        )
        result: Result = await self.session.execute(query)
        rows = result.mappings().all()
        logger.debug(
            f"[conversation] get_partners: user_id={user_id}, count={len(rows)}"
        )
        return rows

    async def add_conversation(self, user_id: int, recipient_id: int) -> bool:
        """Добавляет запись чата. Возвращает True если добавлено, False если уже существует."""
        stmt = (
            pg_insert(Conversation)
            .values(user_id=user_id, recipient_id=recipient_id)
            .on_conflict_do_nothing(constraint="uq_conversation_pair")
            .returning(Conversation.id)
        )
        result: Result = await self.session.execute(stmt)
        inserted = result.fetchone()
        logger.debug(
            f"[conversation] add: user_id={user_id}, recipient_id={recipient_id}, inserted={inserted is not None}"
        )
        return inserted is not None

    async def delete_conversation(self, user_id: int, recipient_id: int) -> bool:
        """Удаляет запись чата из списка бесед. Сообщения не затрагиваются."""
        stmt = delete(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.recipient_id == recipient_id,
        )
        result: Result = await self.session.execute(stmt)
        deleted = result.rowcount > 0
        logger.debug(
            f"[conversation] delete: user_id={user_id}, recipient_id={recipient_id}, deleted={deleted}"
        )
        return deleted

    async def get_available_users(self, user_id: int) -> Sequence:
        """Возвращает пользователей, с которыми у текущем пользователем ещё нет чата."""
        current_recipients = select(Conversation.recipient_id).where(
            Conversation.user_id == user_id
        )
        query = (
            select(User.__table__.columns)
            .where(User.id != user_id)
            .where(User.id.not_in(current_recipients))
            .order_by(User.full_name)
        )
        result: Result = await self.session.execute(query)
        rows = result.mappings().all()
        logger.debug(
            f"[conversation] get_available_users: user_id={user_id}, count={len(rows)}"
        )
        return rows
