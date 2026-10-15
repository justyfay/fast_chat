from datetime import UTC, datetime, timedelta

import pytest
from async_asgi_testclient import TestClient
from fastapi import status
from jose import jwt
from redis.asyncio import Redis

from fast_chat.config import settings
from fast_chat.constants import AuthData
from fast_chat.main import app
from fast_chat.utils.auth import create_access_token

from ....constants import RoutersTestData, TokenTestData
from ....utils.auth import UserData, login_user


def with_token(token: str) -> dict:
    """Cookie с токеном для запроса от клиента без cookie."""
    return {"access_token": token}


async def test_error_token_after_logout(
    user_one: UserData, main_client: TestClient
) -> None:
    """Ошибка 401 при запросе со старым токеном, после выхода из системы."""
    # Arrange
    token = await login_user(main_client, user_one.email, user_one.password)
    client = TestClient(app)
    before = await client.get(
        RoutersTestData.CURRENT_USER_URL, cookies=with_token(token)
    )
    assert before.status_code == status.HTTP_200_OK
    logout = await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token))
    assert logout.status_code == status.HTTP_200_OK

    # Act
    resp = await client.get(RoutersTestData.CURRENT_USER_URL, cookies=with_token(token))

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert TokenTestData.REVOKED_MESSAGE in resp.json()["detail"]


async def test_websocket_with_revoked_token_is_rejected(
    user_one: UserData, main_client: TestClient
) -> None:
    """Отклоняется подключение к WebSocket с токеном, отозванным при выходе."""
    # Arrange
    token = await login_user(main_client, user_one.email, user_one.password)
    client = TestClient(app)
    ws_url = RoutersTestData.WS_URL.format(user_id=user_one.id)
    async with client.websocket_connect(ws_url, cookies=with_token(token)):
        pass
    await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token))

    # Act / Assert
    with pytest.raises(AssertionError):
        async with client.websocket_connect(ws_url, cookies=with_token(token)):
            pass


async def test_logout_revokes_only_current_session(
    user_one: UserData, main_client: TestClient
) -> None:
    """Выход из системы отзывает текущий токен, другая сессия
    того же пользователя продолжает работать."""
    # Arrange
    first = await login_user(main_client, user_one.email, user_one.password)
    second = await login_user(main_client, user_one.email, user_one.password)
    client = TestClient(app)
    await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(first))

    # Act
    resp = await client.get(
        RoutersTestData.CURRENT_USER_URL, cookies=with_token(second)
    )

    # Assert
    assert first != second
    assert resp.status_code == status.HTTP_200_OK


async def test_logout_does_not_revoke_other_users_token(
    user_one: UserData,
    user_two: UserData,
    main_client: TestClient,
    other_client: TestClient,
) -> None:
    """Выход одного пользователя не затрагивает токен другого пользователя."""
    # Arrange
    token_one = await login_user(main_client, user_one.email, user_one.password)
    token_two = await login_user(other_client, user_two.email, user_two.password)
    client = TestClient(app)
    await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token_one))

    # Act
    resp = await client.get(
        RoutersTestData.CURRENT_USER_URL, cookies=with_token(token_two)
    )

    # Assert
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "cookies",
    [
        pytest.param({}, id="no-cookie"),
        pytest.param({"access_token": TokenTestData.GARBAGE_TOKEN}, id="garbage-token"),
    ],
)
async def test_logout_without_valid_token_returns_ok(
    cookies: dict, main_client: TestClient
) -> None:
    """Отсутствуют ошибки при выходе без cookie или с невалидным токеном."""
    # Arrange
    client = TestClient(app)

    # Act
    resp = await client.post(RoutersTestData.LOGOUT_URL, cookies=cookies)

    # Assert
    assert resp.status_code == status.HTTP_200_OK


async def test_logout_twice_with_same_token_returns_ok(
    user_one: UserData, main_client: TestClient
) -> None:
    """Отсутствуют ошибки при выходе с тем же токеном."""
    # Arrange
    token = await login_user(main_client, user_one.email, user_one.password)
    client = TestClient(app)
    await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token))

    # Act
    resp = await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token))

    # Assert
    assert resp.status_code == status.HTTP_200_OK


async def test_revoked_token_record_lives_no_longer_than_token(
    user_one: UserData, main_client: TestClient, redis_connection: Redis
) -> None:
    """По истечению токена запись об отозванном токене в Redis исчезает."""
    # Arrange
    token = await login_user(main_client, user_one.email, user_one.password)
    jti = jwt.get_unverified_claims(token)["jti"]
    client = TestClient(app)

    # Act
    await client.post(RoutersTestData.LOGOUT_URL, cookies=with_token(token))

    # Assert
    ttl = await redis_connection.ttl(AuthData.REVOKED_TOKEN_KEY.format(jti=jti))
    assert 0 < ttl <= settings.access_token_expire_minutes * 60


async def test_error_token_without_jti(
    user_one: UserData, main_client: TestClient
) -> None:
    """Ошибка 401 при использовании токена без jti."""
    # Arrange
    token = jwt.encode(
        {"sub": user_one.email, "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    client = TestClient(app)

    # Act
    resp = await client.get(RoutersTestData.CURRENT_USER_URL, cookies=with_token(token))

    # Assert
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    ("method", "url"),
    [
        pytest.param("get", RoutersTestData.CURRENT_USER_URL, id="current-user"),
        pytest.param("post", RoutersTestData.LOGOUT_URL, id="logout"),
    ],
)
async def test_error_returns_503_when_redis_is_unavailable(
    method: str, url: str, redis_unavailable: None
) -> None:
    """Токена и запрос на выход из системы отдают ошибку 503 при недоступности Redis."""
    # Arrange
    token = create_access_token({"sub": TokenTestData.SUBJECT})
    client = TestClient(app)

    # Act
    resp = await getattr(client, method)(url, cookies=with_token(token))

    # Assert
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
