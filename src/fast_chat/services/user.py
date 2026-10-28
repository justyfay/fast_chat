from typing import Sequence

from sqlalchemy import RowMapping

from fast_chat.dao.user import UserDAO


class UserService:
    """Работа с пользователями."""

    def __init__(self, users: UserDAO) -> None:
        """
        :param users: DAO пользователей
        """
        self.users = users

    async def get_by_username(self, username: str) -> RowMapping | None:
        """
        Возвращает пользователя по имени (username) или None.

        :param username: Имя пользователя (совпадает с email)
        """
        return await self.users.find_one_or_none(username=username)

    async def get_by_id(self, user_id: int) -> RowMapping | None:
        """
        Возвращает пользователя по id или None.

        :param user_id: Идентификатор пользователя
        """
        return await self.users.find_one_or_none(id=user_id)

    async def get_all(self) -> Sequence[RowMapping]:
        """Возвращает всех пользователей."""
        return await self.users.find_all()
