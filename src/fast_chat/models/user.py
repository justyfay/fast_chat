from datetime import datetime, UTC

from sqlalchemy import DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from fast_chat.database import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        Index("uq_user_email_lower", text("lower(email)"), unique=True),
        Index("uq_user_username_lower", text("lower(username)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    username: Mapped[str]
    full_name: Mapped[str]
    telegram_unic_code: Mapped[int] = mapped_column(nullable=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC).replace(tzinfo=None)
    )

    def __str__(self):
        return "Id: {}, username: {}, fullname: {},  telegram_unic_code: {}".format(
            self.id, self.username, self.full_name, self.telegram_unic_code
        )
