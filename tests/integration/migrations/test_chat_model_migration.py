import pytest
from alembic import command

from ...constants import MigrationTestData
from ...utils.migrate import run_sql

ALISSON, COURTOIS, DE_GEA = 1, 2, 3

# Сообщения старой схемы: (отправитель, получатель, текст).
OLD_MESSAGES = [
    (ALISSON, COURTOIS, "one"),
    (COURTOIS, ALISSON, "two"),
    (ALISSON, COURTOIS, "three"),
    (ALISSON, DE_GEA, "four"),
]
OLD_CONVERSATIONS = [(ALISSON, COURTOIS), (DE_GEA, ALISSON), (COURTOIS, DE_GEA)]


@pytest.fixture
def old_schema(schema_at):
    """Схема на ревизии до чатов."""
    return schema_at(MigrationTestData.BEFORE_CHAT_MODEL_REVISION)


def _seed_old_data() -> None:
    run_sql(
        *[
            (MigrationTestData.USER_INSERT, (f"{name}@example.com", name))
            for name in ("alisson", "courtois", "de.gea")
        ],
        *[(MigrationTestData.OLD_MESSAGE_INSERT, row) for row in OLD_MESSAGES],
        *[
            (MigrationTestData.OLD_CONVERSATION_INSERT, row)
            for row in OLD_CONVERSATIONS
        ],
    )


def test_migration_moves_all_messages_into_direct_chats(old_schema) -> None:
    """После миграции количество сообщений прежнее, у каждого есть чат, чатов столько, сколько собеседников."""
    # Arrange
    _seed_old_data()

    # Act
    command.upgrade(old_schema, "head")

    # Assert
    assert run_sql(("SELECT count(*) AS n FROM message", ()))[0]["n"] == len(
        OLD_MESSAGES
    )
    assert (
        run_sql(("SELECT count(*) AS n FROM message WHERE chat_id IS NULL", ()))[0]["n"]
        == 0
    )
    chats = run_sql(("SELECT direct_key FROM chat ORDER BY direct_key", ()))
    assert [row["direct_key"] for row in chats] == ["1:2", "1:3", "2:3"]
    messages = run_sql(
        (
            "SELECT m.body, m.sender_id, c.direct_key, m.created_at FROM message m "
            "JOIN chat c ON c.id = m.chat_id ORDER BY m.id",
            (),
        )
    )
    assert [(row["body"], row["direct_key"]) for row in messages] == [
        ("one", "1:2"),
        ("two", "1:2"),
        ("three", "1:2"),
        ("four", "1:3"),
    ]
    assert all(row["created_at"] is not None for row in messages)


def test_migration_adds_both_users_to_each_chat(old_schema) -> None:
    """Каждый личный чат получает обоих участников, старые таблица и колонка удалены."""
    # Arrange
    _seed_old_data()

    # Act
    command.upgrade(old_schema, "head")

    # Assert
    members = run_sql(
        (
            "SELECT c.direct_key, array_agg(cm.user_id ORDER BY cm.user_id) AS users "
            "FROM chat_member cm JOIN chat c ON c.id = cm.chat_id "
            "GROUP BY c.direct_key ORDER BY c.direct_key",
            (),
        )
    )
    assert [(row["direct_key"], row["users"]) for row in members] == [
        ("1:2", [1, 2]),
        ("1:3", [1, 3]),
        ("2:3", [2, 3]),
    ]
    tables = run_sql(("SELECT tablename FROM pg_tables WHERE schemaname='public'", ()))
    assert "conversation" not in {row["tablename"] for row in tables}
    columns = run_sql(
        (
            "SELECT column_name FROM information_schema.columns WHERE table_name='message'",
            (),
        )
    )
    assert "recipient_id" not in {row["column_name"] for row in columns}


def test_migration_on_empty_database(old_schema) -> None:
    """На пустой БД миграция проходит и ничего не создаёт."""
    # Act
    command.upgrade(old_schema, "head")

    # Assert
    assert run_sql(("SELECT count(*) AS n FROM chat", ()))[0]["n"] == 0


def test_downgrade_restores_messages_and_conversations(old_schema) -> None:
    """Откат возвращает сообщения с прежними отправителем, получателем и текстом, а беседы - как минимум прежние."""
    # Arrange
    _seed_old_data()
    command.upgrade(old_schema, "head")

    # Act
    command.downgrade(old_schema, MigrationTestData.BEFORE_CHAT_MODEL_REVISION)

    # Assert
    messages = run_sql(
        ("SELECT sender_id, recipient_id, body FROM message ORDER BY id", ())
    )
    assert [
        (row["sender_id"], row["recipient_id"], row["body"]) for row in messages
    ] == OLD_MESSAGES
    conversations = run_sql(("SELECT user_id, recipient_id FROM conversation", ()))
    assert set(OLD_CONVERSATIONS) <= {
        (row["user_id"], row["recipient_id"]) for row in conversations
    }


def test_downgrade_stops_if_group_chats_exist(old_schema) -> None:
    """Откат останавливается, если есть чаты не личного типа: старая схема их не хранит."""
    # Arrange
    command.upgrade(old_schema, "head")
    run_sql(("INSERT INTO chat (type) VALUES ('group')", ()))

    # Act
    with pytest.raises(RuntimeError, match="не личного типа"):
        command.downgrade(old_schema, MigrationTestData.BEFORE_CHAT_MODEL_REVISION)

    # Assert
    assert run_sql(("SELECT count(*) AS n FROM chat", ()))[0]["n"] == 1
