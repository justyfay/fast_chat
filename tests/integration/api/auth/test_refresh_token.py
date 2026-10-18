import asyncio
import time
from datetime import timedelta

import pytest
from async_asgi_testclient import TestClient
from asyncpg import Connection
from fastapi import status
from jose import jwt
from redis.asyncio import Redis

from fast_chat.constants import AuthData
from fast_chat.main import app
from fast_chat.utils.auth import create_access_token
from fast_chat.utils.refresh_tokens import hash_token
from fast_chat.utils.token_revocation import revoke_session

from ....constants import RoutersTestData, TokenTestData
from ....utils.auth import UserData
from ....utils.types import CookiesGetter, CookiesRequest, SessionStarter


async def test_login_sets_access_and_refresh_cookies(user_one: UserData) -> None:
    """При авторизации выдается refresh и access-токены."""
    # Arrange
    client = TestClient(app)

    # Act
    resp = await client.post(
        RoutersTestData.LOGIN_URL,
        form={"username": user_one.email, "password": user_one.password},
    )

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert client.cookie_jar["access_token"]["httponly"]
    refresh_cookie = client.cookie_jar[AuthData.REFRESH_COOKIE]
    assert refresh_cookie["httponly"]
    assert refresh_cookie["path"] == AuthData.REFRESH_COOKIE_PATH
    assert refresh_cookie["samesite"].lower() == "strict"


async def test_refresh_rotates_tokens(
    user_one: UserData,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    current_user: CookiesRequest,
    cookies_of: CookiesGetter,
) -> None:
    """Обновление выдаёт новые рабочие access и refresh."""
    # Arrange
    old = await start_session(user_one)

    # Act
    resp = await refresh(old)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    new = cookies_of(resp)
    assert new["refresh_token"] != old["refresh_token"]
    assert new["access_token"] != old["access_token"]
    assert resp.json()["access_token"] == new["access_token"]
    assert (await current_user(new)).status_code == status.HTTP_200_OK


async def test_refresh_keeps_session_id(
    user_one: UserData,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    cookies_of: CookiesGetter,
) -> None:
    """После обновления sid и его сессия не изменяется."""
    # Arrange
    old = await start_session(user_one)

    # Act
    new = cookies_of(await refresh(old))

    # Assert
    old_sid = jwt.get_unverified_claims(old["access_token"])["sid"]
    assert jwt.get_unverified_claims(new["access_token"])["sid"] == old_sid


async def test_old_refresh_within_grace_gets_409_and_keeps_session(
    user_one: UserData,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    cookies_of: CookiesGetter,
) -> None:
    """
    При повторном использованим refresh
    в пределах лимита не отзывается сессия.
    """
    # Arrange
    old = await start_session(user_one)
    new = cookies_of(await refresh(old))

    # Act
    resp = await refresh(old)

    # Assert
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert (await refresh(new)).status_code == status.HTTP_200_OK


async def test_old_refresh_after_grace_revokes_session(
    user_one: UserData,
    redis_connection: Redis,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    current_user: CookiesRequest,
    cookies_of: CookiesGetter,
) -> None:
    """
    При повторном использовании refresh, выхоядщем за лимит,
     сессия отзывается целиком."""
    # Arrange
    old = await start_session(user_one)
    new = cookies_of(await refresh(old))
    sid = jwt.get_unverified_claims(old["access_token"])["sid"]
    used_key = AuthData.REFRESH_USED_KEY.format(
        token_hash=hash_token(old["refresh_token"])
    )
    long_ago = time.time() - TokenTestData.USED_LONG_AGO_SECONDS
    await redis_connection.set(used_key, f"{long_ago} {sid}", keepttl=True)

    # Act
    resp = await refresh(old)

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert (await refresh(new)).status_code == status.HTTP_401_UNAUTHORIZED
    revoked = await current_user(new)
    assert revoked.status_code == status.HTTP_401_UNAUTHORIZED
    assert TokenTestData.REVOKED_MESSAGE in revoked.json()["detail"]


async def test_concurrent_refresh_gives_one_new_pair(
    user_one: UserData, start_session: SessionStarter, refresh: CookiesRequest
) -> None:
    """При одновременном вызове refresh, второй вызов получает 409."""
    # Arrange
    old = await start_session(user_one)

    # Act
    responses = await asyncio.gather(refresh(old), refresh(old))

    # Assert
    assert sorted(resp.status_code for resp in responses) == [
        status.HTTP_200_OK,
        status.HTTP_409_CONFLICT,
    ]


@pytest.mark.parametrize(
    "cookies",
    [
        pytest.param({}, id="no-cookie"),
        pytest.param({"refresh_token": "unknown-token"}, id="unknown-token"),
    ],
)
async def test_error_refresh_without_valid_token(
    cookies: dict, user_one: UserData, refresh: CookiesRequest
) -> None:
    """Обновление без refresh-cookie или с неизвестным токеном получает 401."""
    # Act
    resp = await refresh(cookies)

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_error_refresh_of_revoked_session(
    user_one: UserData,
    redis_connection: Redis,
    start_session: SessionStarter,
    refresh: CookiesRequest,
) -> None:
    """
    Если сессия уже отозвана, но запись о refresh ещё жива,
    обновление не выдаёт новую пару access-refresh токенов,
    а повторный запрос не считается гонкой.
    """
    # Arrange
    session = await start_session(user_one)
    sid = jwt.get_unverified_claims(session["access_token"])["sid"]
    await revoke_session(redis_connection, sid)
    keys_before = set(await redis_connection.keys("refresh*"))

    # Act
    first = await refresh(session)
    second = await refresh(session)

    # Assert
    assert first.status_code == status.HTTP_401_UNAUTHORIZED
    assert second.status_code == status.HTTP_401_UNAUTHORIZED
    keys_after = set(await redis_connection.keys("refresh*"))
    assert not any(key.startswith("refresh:") for key in keys_after - keys_before)
    assert await redis_connection.get(
        AuthData.SESSION_REFRESH_KEY.format(sid=sid)
    ) == hash_token(session["refresh_token"])


async def test_logout_ends_whole_session(
    user_one: UserData,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    current_user: CookiesRequest,
    cookies_of: CookiesGetter,
) -> None:
    """Выход завершает сессию, refresh и access-токены отозваны."""
    # Arrange
    session = await start_session(user_one)
    first_refresh = cookies_of(await refresh(session))

    # Act
    logout = await TestClient(app).post(
        RoutersTestData.LOGOUT_URL, cookies=first_refresh
    )

    # Assert
    assert logout.status_code == status.HTTP_200_OK
    assert (await refresh(first_refresh)).status_code == status.HTTP_401_UNAUTHORIZED
    # Старый access той же сессии (до обновления) тоже больше не действует
    assert (await current_user(session)).status_code == status.HTTP_401_UNAUTHORIZED


async def test_logout_with_only_refresh_cookie_ends_session(
    user_one: UserData, start_session: SessionStarter, refresh: CookiesRequest
) -> None:
    """Выход только с refresh-cookie завершает сессию"""
    # Arrange
    session = await start_session(user_one)

    # Act
    logout = await TestClient(app).post(
        RoutersTestData.LOGOUT_URL, cookies={"refresh_token": session["refresh_token"]}
    )

    # Assert
    assert logout.status_code == status.HTTP_200_OK
    assert (await refresh(session)).status_code == status.HTTP_401_UNAUTHORIZED


async def test_logout_does_not_end_other_session_of_same_user(
    user_one: UserData,
    start_session: SessionStarter,
    refresh: CookiesRequest,
    current_user: CookiesRequest,
) -> None:
    """Выход на одном устройстве не завершает сессию на другом"""
    # Arrange
    first = await start_session(user_one)
    second = await start_session(user_one)

    # Act
    await TestClient(app).post(RoutersTestData.LOGOUT_URL, cookies=first)

    # Assert
    assert (await current_user(second)).status_code == status.HTTP_200_OK
    assert (await refresh(second)).status_code == status.HTTP_200_OK


async def test_error_refresh_for_deleted_user(
    user_one: UserData,
    pg_conn: Connection,
    start_session: SessionStarter,
    refresh: CookiesRequest,
) -> None:
    """Если пользователя удалили, обновление сессии получает 401"""
    # Arrange
    session = await start_session(user_one)
    await pg_conn.execute('DELETE FROM "user"')

    # Act
    resp = await refresh(session)

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_expired_access_gets_401_json_for_api(
    user_one: UserData, current_user: CookiesRequest
) -> None:
    """Просроченный access на ручке API получает 401."""
    # Arrange
    token = create_access_token({"sub": user_one.email}, timedelta(minutes=-1))

    # Act
    resp = await current_user({"access_token": token})

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert TokenTestData.EXPIRED_MESSAGE in resp.json()["detail"]


async def test_expired_access_redirects_page_to_login(user_one: UserData) -> None:
    """Редирект на страницу входа при просроченном access-токене."""
    # Arrange
    token = create_access_token({"sub": user_one.email}, timedelta(minutes=-1))

    # Act
    resp = await TestClient(app).get(
        RoutersTestData.CHAT_PAGE_URL,
        cookies={"access_token": token},
        allow_redirects=False,
    )

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL


async def test_websocket_of_ended_session_is_rejected(
    user_one: UserData, start_session: SessionStarter
) -> None:
    """Подключение к WebSocket с access-токеном истекшей сессии отклоняется."""
    # Arrange
    session = await start_session(user_one)
    # Тестовый клиент WebSocket склеивает несколько cookie некорректно,
    # поэтому передаём только access
    ws_cookies = {"access_token": session["access_token"]}
    ws_url = RoutersTestData.WS_URL.format(user_id=user_one.id)
    async with TestClient(app).websocket_connect(ws_url, cookies=ws_cookies):
        pass
    await TestClient(app).post(RoutersTestData.LOGOUT_URL, cookies=session)

    # Act / Assert
    with pytest.raises(AssertionError):
        async with TestClient(app).websocket_connect(ws_url, cookies=ws_cookies):
            pass


async def test_refresh_is_rate_limited(
    user_one: UserData, rate_limit_enabled: None, refresh: CookiesRequest
) -> None:
    """Ошибка 429 при привышении лимита запросов на refresh."""
    # Act
    statuses = [
        (await refresh({"refresh_token": "unknown-token"})).status_code
        for _ in range(31)
    ]

    # Assert
    assert statuses.count(status.HTTP_401_UNAUTHORIZED) == 30
    assert statuses[-1] == status.HTTP_429_TOO_MANY_REQUESTS


async def test_error_refresh_if_redis_is_unavailable(
    redis_unavailable: None, refresh: CookiesRequest
) -> None:
    """Ошибка 503 при refresh с недоступным Redis."""
    # Act
    resp = await refresh({"refresh_token": "any-token"})

    # Assert
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
