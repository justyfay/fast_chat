import asyncio

import asyncpg
import pytest
from alembic import command

from fast_chat.config import settings

from ...constants import MigrationTestData
from ...utils.migrate import clear_pg_database, get_alembic_config


async def _run(*queries: tuple[str, tuple]) -> list[asyncpg.Record]:
    """Выполняет запросы в тестовой БД и возвращает результат последнего."""
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
    )
    try:
        result: list[asyncpg.Record] = []
        for query, args in queries:
            result = await conn.fetch(query, *args)
        return result
    finally:
        await conn.close()


async def _clear() -> None:
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
    )
    try:
        await clear_pg_database(conn)
    finally:
        await conn.close()


@pytest.fixture
def schema_before_user_unique(database_ready: None):
    """Схема на ревизии до уникальных индексов. После теста данные чистятся, схема возвращается на head."""
    config = get_alembic_config()
    asyncio.run(_clear())
    command.downgrade(config, MigrationTestData.BEFORE_USER_UNIQUE_REVISION)
    try:
        yield config
    finally:
        asyncio.run(_clear())
        command.upgrade(config, "head")


def test_migration_stops_on_duplicates_ignoring_case(
    schema_before_user_unique,
) -> None:
    """Миграция останавливается с понятным сообщением, если в БД есть email, повторяющиеся без учёта регистра."""
    # Arrange
    asyncio.run(
        _run(
            (MigrationTestData.USER_INSERT, ("Alisson@example.com", "Alisson Becker")),
            (MigrationTestData.USER_INSERT, ("alisson@example.com", "Alisson B.")),
        )
    )

    # Act
    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(schema_before_user_unique, "head")

    # Assert
    assert "alisson@example.com (x2)" in str(exc_info.value)
    emails = asyncio.run(_run(('SELECT email FROM "user" ORDER BY id', ())))
    assert [row["email"] for row in emails] == [
        "Alisson@example.com",
        "alisson@example.com",
    ]


def test_migration_lowercases_existing_emails_and_creates_indexes(
    schema_before_user_unique,
) -> None:
    """Без дублей миграция приводит email и username к нижнему регистру и создаёт уникальные индексы."""
    # Arrange
    asyncio.run(
        _run((MigrationTestData.USER_INSERT, ("Alisson@Example.com", "Alisson Becker")))
    )

    # Act
    command.upgrade(schema_before_user_unique, "head")

    # Assert
    row = asyncio.run(_run(('SELECT email, username FROM "user"', ())))[0]
    assert (row["email"], row["username"]) == ("alisson@example.com",) * 2
    indexes = asyncio.run(
        _run(("SELECT indexname FROM pg_indexes WHERE tablename = 'user'", ()))
    )
    assert {"uq_user_email_lower", "uq_user_username_lower"} <= {
        row["indexname"] for row in indexes
    }


def test_migration_downgrade_drops_indexes(schema_before_user_unique) -> None:
    """Откат миграции удаляет уникальные индексы."""
    # Arrange
    command.upgrade(schema_before_user_unique, "head")

    # Act
    command.downgrade(
        schema_before_user_unique, MigrationTestData.BEFORE_USER_UNIQUE_REVISION
    )

    # Assert
    indexes = asyncio.run(
        _run(("SELECT indexname FROM pg_indexes WHERE tablename = 'user'", ()))
    )
    assert not {"uq_user_email_lower", "uq_user_username_lower"} & {
        row["indexname"] for row in indexes
    }
