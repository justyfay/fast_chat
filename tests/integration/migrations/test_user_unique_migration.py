import pytest
from alembic import command

from ...constants import MigrationTestData
from ...utils.migrate import run_sql

USER_INDEXES = {"uq_user_email_lower", "uq_user_username_lower"}


@pytest.fixture
def schema_before_user_unique(schema_at):
    """Схема на ревизии до уникальных индексов."""
    return schema_at(MigrationTestData.BEFORE_USER_UNIQUE_REVISION)


def _user_indexes() -> set[str]:
    rows = run_sql(("SELECT indexname FROM pg_indexes WHERE tablename = 'user'", ()))
    return {row["indexname"] for row in rows}


def test_migration_stops_on_duplicates_ignoring_case(
    schema_before_user_unique,
) -> None:
    """Миграция останавливается с понятным сообщением, если в БД есть email, повторяющиеся без учёта регистра"""
    # Arrange
    run_sql(
        (MigrationTestData.USER_INSERT, ("Alisson@example.com", "Alisson Becker")),
        (MigrationTestData.USER_INSERT, ("alisson@example.com", "Alisson B.")),
    )

    # Act
    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(
            schema_before_user_unique, MigrationTestData.USER_UNIQUE_REVISION
        )

    # Assert
    assert "alisson@example.com (x2)" in str(exc_info.value)
    emails = run_sql(('SELECT email FROM "user" ORDER BY id', ()))
    assert [row["email"] for row in emails] == [
        "Alisson@example.com",
        "alisson@example.com",
    ]


def test_migration_lowercases_existing_emails_and_creates_indexes(
    schema_before_user_unique,
) -> None:
    """Без дублей миграция приводит email и username к нижнему регистру и создаёт уникальные индексы."""
    # Arrange
    run_sql((MigrationTestData.USER_INSERT, ("Alisson@Example.com", "Alisson Becker")))

    # Act
    command.upgrade(schema_before_user_unique, MigrationTestData.USER_UNIQUE_REVISION)

    # Assert
    row = run_sql(('SELECT email, username FROM "user"', ()))[0]
    assert (row["email"], row["username"]) == ("alisson@example.com",) * 2
    assert USER_INDEXES <= _user_indexes()


def test_migration_downgrade_drops_indexes(schema_before_user_unique) -> None:
    """Откат миграции удаляет уникальные индексы."""
    # Arrange
    command.upgrade(schema_before_user_unique, MigrationTestData.USER_UNIQUE_REVISION)

    # Act
    command.downgrade(
        schema_before_user_unique, MigrationTestData.BEFORE_USER_UNIQUE_REVISION
    )

    # Assert
    assert not USER_INDEXES & _user_indexes()
