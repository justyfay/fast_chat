from typing import Any, AsyncIterator, Iterator

import asyncpg
import pytest
import redis.asyncio as redis
from async_asgi_testclient import TestClient
from asyncpg import Connection
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from fast_chat.config import settings
from fast_chat.dependencies.database import get_session, get_session_factory
from fast_chat.dependencies.rate_limit import (
    login_rate_limit,
    refresh_rate_limit,
    register_rate_limit,
)
from fast_chat.dependencies.redis import get_redis
from fast_chat.main import app
from fast_chat.routers.v1.ws import active_connections
from .constants import RoutersTestData
from .dependencies import build_get_session, build_session_factory
from .utils.auth import UserData, register_and_login
from .utils.types import CookiesGetter, CookiesRequest, SessionStarter
from .utils.lock import release_test_db_lock, try_acquire_test_db_lock
from .utils.migrate import (
    assert_test_database,
    clear_pg_database,
    create_pg_database,
    upgrade_pg_schema,
)

TEST_REDIS_DB = 15


def pytest_collection_finish(session: pytest.Session) -> None:
    """Не даёт запустить два прогона с БД одновременно: оба чистят одни и те же таблицы.

    Проверка включается, только если среди собранных тестов есть те, что используют БД,
    поэтому отдельный запуск unit-тестов не блокируется.
    """
    if session.config.option.collectonly:
        return
    if not any("database_ready" in item.fixturenames for item in session.items):
        return
    if not try_acquire_test_db_lock():
        pytest.exit(
            f"Тесты уже запущены в другом процессе и используют БД '{settings.db_name}'. "
            "Дождитесь завершения существующего прогона и запустите тесты снова.",
            returncode=1,
        )


def pytest_sessionfinish(session: pytest.Session) -> None:
    release_test_db_lock()


@pytest.fixture(scope="session")
def database_ready() -> None:
    """Создаёт тестовую БД (если нет) и применяет миграции. Работает только на `*_test`."""
    assert_test_database(settings.db_name)
    create_pg_database(settings.db_name)
    upgrade_pg_schema()


@pytest.fixture(scope="function")
async def pg_conn(database_ready: None) -> AsyncIterator[Connection]:
    """Прямое подключение к тестовой БД: чистит данные до и после каждого теста."""
    conn = await asyncpg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
    )
    await clear_pg_database(conn)
    try:
        yield conn
    finally:
        await clear_pg_database(conn)
        await conn.close()


@pytest.fixture(scope="function")
async def engine(pg_conn: Connection) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, autoflush=False) as session:
        yield session


@pytest.fixture(scope="function")
async def redis_connection() -> AsyncIterator[Redis]:
    """Redis на отдельной БД (не 0), чтобы не затронуть очередь Celery dev-окружения."""
    redis_client = redis.from_url(
        f"{settings.redis_url}/{TEST_REDIS_DB}", decode_responses=True
    )
    await redis_client.flushdb()
    yield redis_client
    await redis_client.flushdb()
    await redis_client.aclose()


async def no_rate_limit() -> None:
    """Заглушка лимитера для обычных тестов."""


def disable_rate_limits() -> None:
    app.dependency_overrides[login_rate_limit] = no_rate_limit
    app.dependency_overrides[register_rate_limit] = no_rate_limit
    app.dependency_overrides[refresh_rate_limit] = no_rate_limit


@pytest.fixture(scope="function")
def db_override(engine: AsyncEngine, redis_connection: Redis) -> Iterator[None]:
    app.dependency_overrides[get_session] = build_get_session(engine)
    app.dependency_overrides[get_session_factory] = build_session_factory(engine)
    app.dependency_overrides[get_redis] = lambda: redis_connection
    disable_rate_limits()
    active_connections.clear()
    yield
    active_connections.clear()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def main_client(db_override: None) -> AsyncIterator[TestClient]:
    async with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def other_client(db_override: None) -> AsyncIterator[TestClient]:
    """Второй клиент со своим cookie_jar: второй пользователь в тестах с двумя участниками."""
    async with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def real_db_client(
    pg_conn: Connection, redis_connection: Redis
) -> AsyncIterator[TestClient]:
    """Клиент на настоящего приложения с lifespan и общим пулом БД;
    Redis тестовый, чтобы не оставлять токены в рабочем."""
    app.dependency_overrides[get_redis] = lambda: redis_connection
    disable_rate_limits()
    async with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def rate_limit_enabled(db_override: None) -> Iterator[None]:
    """Включает настоящие лимитеры в тестовой БД Redis."""
    app.dependency_overrides.pop(login_rate_limit)
    app.dependency_overrides.pop(register_rate_limit)
    app.dependency_overrides.pop(refresh_rate_limit)
    yield


@pytest.fixture(scope="function")
async def redis_unavailable(rate_limit_enabled: None) -> AsyncIterator[None]:
    """Подменяет Redis клиентом с невалидным URL."""
    broken_redis = redis.from_url("redis://127.0.0.1:1")
    app.dependency_overrides[get_redis] = lambda: broken_redis
    yield
    await broken_redis.aclose()


@pytest.fixture(scope="function")
async def user_one(main_client: TestClient) -> UserData:
    return await register_and_login(
        main_client, email="alisson@example.com", full_name="Alisson Becker"
    )


@pytest.fixture(scope="function")
async def user_two(other_client: TestClient) -> UserData:
    return await register_and_login(
        other_client, email="courtois@example.com", full_name="Thibaut Courtois"
    )


@pytest.fixture(scope="function")
def cookies_of() -> CookiesGetter:
    """Метод достаёт из ответа сервера cookie с токенами."""

    def get_cookies(resp: Any) -> dict:
        return {
            name: resp.cookies.get(name) for name in ("access_token", "refresh_token")
        }

    return get_cookies


@pytest.fixture(scope="function")
def start_session(db_override: None, cookies_of: CookiesGetter) -> SessionStarter:
    """Метод входит новым клиентом и возвращает cookie начатой сессии."""

    async def start(user: UserData) -> dict:
        resp = await TestClient(app).post(
            RoutersTestData.LOGIN_URL,
            form={"username": user.email, "password": user.password},
        )
        assert resp.status_code == 200, resp.text
        return cookies_of(resp)

    return start


@pytest.fixture(scope="function")
def refresh(db_override: None) -> CookiesRequest:
    """Метод обновления сессии: отправляет `/auth/refresh` с переданными cookie."""

    async def send(cookies: dict) -> Any:
        return await TestClient(app).post(RoutersTestData.REFRESH_URL, cookies=cookies)

    return send


@pytest.fixture(scope="function")
def current_user(db_override: None) -> CookiesRequest:
    """Метод запроса текущего пользователя с переданными cookie."""

    async def send(cookies: dict) -> Any:
        return await TestClient(app).get(
            RoutersTestData.CURRENT_USER_URL, cookies=cookies
        )

    return send
