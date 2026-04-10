from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.fast_chat.database import Base


class Conversation(Base):
    """Запись о том, что пользователь добавил чат с получателем в свой список бесед."""

    __tablename__ = "conversation"
    __table_args__ = (
        UniqueConstraint("user_id", "recipient_id", name="uq_conversation_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)

    def __str__(self) -> str:
        return f"Conversation(user_id={self.user_id}, recipient_id={self.recipient_id})"
