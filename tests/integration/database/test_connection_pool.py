import asyncio

from async_asgi_testclient import TestClient
from asyncpg import Connection
from fastapi import status

from fast_chat.database import MAX_OVERFLOW, POOL_SIZE

from ...constants import RoutersTestData
from ...utils.auth import register_and_login

WARMUP_REQUESTS = 20
TOTAL_REQUESTS = 200
CONCURRENT_REQUESTS = 50


async def count_db_connections(pg_conn: Connection) -> int:
    """Число соединений с тестовой БД без учета подключения теста."""
    return await pg_conn.fetchval(
        "SELECT count(*) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid()"
    )


async def test_db_connections_do_not_grow_with_requests(
    real_db_client: TestClient, pg_conn: Connection
) -> None:
    """После 200 запросов число соединений с БД не больше, чем после первых 20"""
    # Arrange
    await register_and_login(real_db_client)
    for _ in range(WARMUP_REQUESTS):
        await real_db_client.get(RoutersTestData.CURRENT_USER_URL)
    after_warmup = await count_db_connections(pg_conn)

    # Act
    for _ in range(TOTAL_REQUESTS - WARMUP_REQUESTS):
        resp = await real_db_client.get(RoutersTestData.CURRENT_USER_URL)
        assert resp.status_code == status.HTTP_200_OK

    # Assert
    assert await count_db_connections(pg_conn) <= after_warmup


async def test_db_connections_are_limited_by_pool_size(
    real_db_client: TestClient, pg_conn: Connection
) -> None:
    """Параллельные запросы не открывают соединений больше лимита пула"""
    # Arrange
    await register_and_login(real_db_client)

    # Act
    responses = await asyncio.gather(
        *(
            real_db_client.get(RoutersTestData.CURRENT_USER_URL)
            for _ in range(CONCURRENT_REQUESTS)
        )
    )

    # Assert
    assert all(resp.status_code == status.HTTP_200_OK for resp in responses)
    assert await count_db_connections(pg_conn) <= POOL_SIZE + MAX_OVERFLOW
