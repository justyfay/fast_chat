from typing import Sequence

from sqlalchemy import Integer, Result, RowMapping, case, cast, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fast_chat.dao.base import BaseDAO
from fast_chat.database import Base
from fast_chat.logger import get_logger
from fast_chat.models.chat import Chat, ChatMember
from fast_chat.models.user import User

logger = get_logger()


def direct_key(user_id: int, other_id: int) -> str:
    """Ключ личного чата пары: меньший id первым, порядок пользователей не важен."""
    return f"{min(user_id, other_id)}:{max(user_id, other_id)}"


def _partner_id(user_id: int):
    """Id собеседника в личном чате, берётся из `direct_key`.
    Поэтому чат остаётся виден тому, кто не выходил, даже если собеседник из чата ушёл."""
    first = cast(func.split_part(Chat.direct_key, ":", 1), Integer)
    second = cast(func.split_part(Chat.direct_key, ":", 2), Integer)
    return case((first == user_id, second), else_=first)


class ChatDAO(BaseDAO):
    model: type[Base] = Chat
    filterable_fields = frozenset({"id", "direct_key"})

    async def find_direct(self, user_id: int, other_id: int) -> int | None:
        """Возвращает id личного чата двух пользователей или None, если чата нет."""
        chat = await self.find_one_or_none(direct_key=direct_key(user_id, other_id))
        return chat["id"] if chat else None

    async def get_or_create_direct(self, user_id: int, other_id: int) -> int:
        """Возвращает созданный id личного чата двух пользователей."""
        stmt = (
            pg_insert(Chat)
            .values(type="direct", direct_key=direct_key(user_id, other_id))
            .on_conflict_do_nothing(index_elements=[Chat.direct_key])
            .returning(Chat.id)
        )
        created = (await self.session.execute(stmt)).scalar_one_or_none()
        if created is not None:
            return created
        chat_id = await self.find_direct(user_id, other_id)
        assert chat_id is not None
        return chat_id

    async def add_member(self, chat_id: int, user_id: int) -> bool:
        """Добавляет участника. Возвращает False, если он уже в чате."""
        stmt = (
            pg_insert(ChatMember)
            .values(chat_id=chat_id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_chat_member")
            .returning(ChatMember.id)
        )
        added = (await self.session.execute(stmt)).scalar_one_or_none() is not None
        logger.debug(
            f"[chat] add_member: chat_id={chat_id}, user_id={user_id}, added={added}"
        )
        return added

    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        """Убирает участника из чата. Сообщения и чат остаются. Возвращает False, если его там не было."""
        stmt = delete(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
        )
        result: Result = await self.session.execute(stmt)
        removed = result.rowcount > 0
        logger.debug(
            f"[chat] remove_member: chat_id={chat_id}, user_id={user_id}, removed={removed}"
        )
        return removed

    async def get_partners(self, user_id: int) -> Sequence[RowMapping]:
        """Возвращает собеседников из личных чатов пользователя в порядке добавления чатов."""
        query = (
            select(User.__table__.columns)
            .select_from(ChatMember)
            .join(Chat, Chat.id == ChatMember.chat_id)
            .join(User, User.id == _partner_id(user_id))
            .where(ChatMember.user_id == user_id, Chat.type == "direct")
            .where(_partner_id(user_id) != user_id)
            .order_by(ChatMember.id)
        )
        rows = (await self.session.execute(query)).mappings().all()
        logger.debug(f"[chat] get_partners: user_id={user_id}, count={len(rows)}")
        return rows

    async def get_available_users(self, user_id: int) -> Sequence[RowMapping]:
        """Возвращает пользователей, с которыми у пользователя ещё нет личного чата в списке."""
        partners = (
            select(_partner_id(user_id))
            .select_from(ChatMember)
            .join(Chat, Chat.id == ChatMember.chat_id)
            .where(ChatMember.user_id == user_id, Chat.type == "direct")
        )
        query = (
            select(User.__table__.columns)
            .where(User.id != user_id)
            .where(User.id.not_in(partners))
            .order_by(User.full_name)
        )
        rows = (await self.session.execute(query)).mappings().all()
        logger.debug(
            f"[chat] get_available_users: user_id={user_id}, count={len(rows)}"
        )
        return rows
