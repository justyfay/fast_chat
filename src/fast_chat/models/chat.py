from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from fast_chat.database import Base


class Chat(Base):
    """Личный чат (двое участников).

    `direct_key` - пара id участников личного чата («first_id:second_id», меньший id первым),
    по нему находится единственный личный чат пары. У остальных чатов он пустой.
    """

    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(16), server_default="direct")
    direct_key: Mapped[str | None] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatMember(Base):
    """Участие пользователя в чате."""

    __tablename__ = "chat_member"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
