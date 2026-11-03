import asyncio
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config
from asyncpg import Connection

from fast_chat.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def assert_test_database(db_name: str) -> None:
    """Имя тестовой БД должно оканчиваться на `_test`."""
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"Тесты можно запускать только на БД с суффиксом '_test', получено: '{db_name}'."
        )


async def _create_database_if_not_exists(db_name: str) -> None:
    assert_test_database(db_name)
    conn: Connection = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def create_pg_database(db_name: str) -> None:
    """Создаёт тестовую БД, если её ещё нет (вызывается вне event loop)."""
    asyncio.run(_create_database_if_not_exists(db_name))


def get_alembic_config() -> Config:
    """Конфигурация Alembic для тестовой БД."""
    assert_test_database(settings.db_name)
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return alembic_config


def upgrade_pg_schema() -> None:
    """Применяет миграции Alembic к тестовой БД (вызывается вне event loop)."""
    command.upgrade(get_alembic_config(), "head")


async def clear_pg_database(conn: Connection) -> None:
    """Очищает данные всех таблиц, кроме служебной `alembic_version`, и сбрасывает счётчики id."""
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables "
        "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
    )
    if tables:
        names = ", ".join(f'"{table["tablename"]}"' for table in tables)
        await conn.execute(f"TRUNCATE {names} RESTART IDENTITY CASCADE")


async def _fetch(queries: tuple[tuple[str, tuple], ...]) -> list[asyncpg.Record]:
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


def run_sql(*queries: tuple[str, tuple]) -> list[asyncpg.Record]:
    """Выполняет запросы в тестовой БД и возвращает результат последнего (для синхронных тестов миграций)."""
    assert_test_database(settings.db_name)
    return asyncio.run(_fetch(queries))


def clear_data() -> None:
    """Чистит данные всех таблиц тестовой БД на любой ревизии схемы."""

    async def clear() -> None:
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

    assert_test_database(settings.db_name)
    asyncio.run(clear())
