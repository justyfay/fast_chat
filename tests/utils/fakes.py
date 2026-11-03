from types import SimpleNamespace
from typing import Any


class FakeUserDAO:
    """In-memory замена `UserDAO` для unit-тестов сервисов."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def find_one_or_none(self, **filter_by: Any) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in self.rows
                if all(row.get(key) == value for key, value in filter_by.items())
            ),
            None,
        )

    async def find_all(self, **filter_by: Any) -> list[dict[str, Any]]:
        return list(self.rows)

    async def add(self, **data: Any) -> dict[str, int]:
        row = {"id": len(self.rows) + 1, **data}
        self.rows.append(row)
        return {"id": row["id"]}


class FakeChatDAO:
    """In-memory замена `ChatDAO`: личные чаты по ключу пары и участники в порядке добавления."""

    def __init__(self, users: FakeUserDAO) -> None:
        self.users = users
        self.chats: dict[str, int] = {}
        self.members: list[tuple[int, int]] = []

    @staticmethod
    def _key(user_id: int, other_id: int) -> str:
        return f"{min(user_id, other_id)}:{max(user_id, other_id)}"

    def _other(self, chat_id: int, user_id: int) -> int | None:
        key = next(key for key, id_ in self.chats.items() if id_ == chat_id)
        ids = [int(part) for part in key.split(":")]
        others = [id_ for id_ in ids if id_ != user_id]
        return others[0] if others else None

    async def find_direct(self, user_id: int, other_id: int) -> int | None:
        return self.chats.get(self._key(user_id, other_id))

    async def get_or_create_direct(self, user_id: int, other_id: int) -> int:
        return self.chats.setdefault(self._key(user_id, other_id), len(self.chats) + 1)

    async def add_member(self, chat_id: int, user_id: int) -> bool:
        if (chat_id, user_id) in self.members:
            return False
        self.members.append((chat_id, user_id))
        return True

    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        if (chat_id, user_id) not in self.members:
            return False
        self.members.remove((chat_id, user_id))
        return True

    async def get_partners(self, user_id: int) -> list[dict[str, Any]]:
        partner_ids = [
            self._other(chat_id, user_id)
            for chat_id, member_id in self.members
            if member_id == user_id
        ]
        return [
            row
            for partner_id in partner_ids
            if partner_id is not None
            for row in self.users.rows
            if row["id"] == partner_id
        ]

    async def get_available_users(self, user_id: int) -> list[dict[str, Any]]:
        partner_ids = {row["id"] for row in await self.get_partners(user_id)}
        return [
            row
            for row in self.users.rows
            if row["id"] != user_id and row["id"] not in partner_ids
        ]


class FakeMessageDAO:
    """In-memory замена `MessageDAO`: хранит сообщения так же, как БД (тело как передали)."""

    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []

    async def add(self, **data: Any) -> dict[str, int]:
        row = SimpleNamespace(id=len(self.rows) + 1, **data)
        self.rows.append(row)
        return {"id": row.id}

    async def get_chat_messages(self, chat_id: int) -> list[SimpleNamespace]:
        return [row for row in self.rows if row.chat_id == chat_id]
