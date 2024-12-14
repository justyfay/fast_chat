from logger import get_logger
from src.fast_chat.dao.base import BaseDAO
from src.fast_chat.database import Base
from src.fast_chat.models.user import User

logger = get_logger()


class UserDAO(BaseDAO):
    model: type[Base] = User
