from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from fast_chat.database import Base


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (Index("ix_message_chat_id_id", "chat_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __str__(self):
        return "Id: {}, chat_id: {}, sender_id: {}, message: {} ".format(
            self.id, self.chat_id, self.sender_id, self.body
        )
