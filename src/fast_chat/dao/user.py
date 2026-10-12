from fast_chat.logger import get_logger
from fast_chat.dao.base import BaseDAO
from fast_chat.database import Base
from fast_chat.models.user import User

logger = get_logger()


class UserDAO(BaseDAO):
    model: type[Base] = User
