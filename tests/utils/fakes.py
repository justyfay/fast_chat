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


class FakeConversationDAO:
    """In-memory замена `ConversationDAO`, пары «отправитель - получатель» в порядке добавления."""

    def __init__(self, users: FakeUserDAO) -> None:
        self.users = users
        self.pairs: list[tuple[int, int]] = []

    async def get_partners(self, user_id: int) -> list[dict[str, Any]]:
        return [
            row
            for owner, recipient in self.pairs
            if owner == user_id
            for row in self.users.rows
            if row["id"] == recipient
        ]

    async def add_conversation(self, user_id: int, recipient_id: int) -> bool:
        if (user_id, recipient_id) in self.pairs:
            return False
        self.pairs.append((user_id, recipient_id))
        return True

    async def delete_conversation(self, user_id: int, recipient_id: int) -> bool:
        if (user_id, recipient_id) not in self.pairs:
            return False
        self.pairs.remove((user_id, recipient_id))
        return True

    async def get_available_users(self, user_id: int) -> list[dict[str, Any]]:
        added = {recipient for owner, recipient in self.pairs if owner == user_id}
        return [
            row
            for row in self.users.rows
            if row["id"] != user_id and row["id"] not in added
        ]


class FakeMessageDAO:
    """In-memory замена `MessageDAO`, хранит сообщения так же, как БД."""

    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []

    async def add(self, **data: Any) -> dict[str, int]:
        row = SimpleNamespace(id=len(self.rows) + 1, **data)
        self.rows.append(row)
        return {"id": row.id}

    async def get_messages_between_users(
        self, user_id_1: int, user_id_2: int
    ) -> list[SimpleNamespace]:
        return [
            row
            for row in self.rows
            if {row.sender_id, row.recipient_id} == {user_id_1, user_id_2}
        ]
