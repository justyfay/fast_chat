from datetime import datetime, UTC

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.fast_chat.database import Base


class User(Base):
    __tablename__ = "user"

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
