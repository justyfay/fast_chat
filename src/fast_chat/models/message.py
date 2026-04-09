from sqlalchemy import Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.fast_chat.database import Base


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(Text)

    def __str__(self):
        return "Id: {}, sender_id: {}, recipient_id: {}, message: {} ".format(
            self.id, self.sender_id, self.recipient_id, self.body
        )
