import asyncio

import pytest
from async_asgi_testclient import TestClient
from fastapi import status

from fast_chat.main import app

from ....constants import RateLimitTestData, RoutersTestData
from ....utils.auth import register_payload


async def try_unknown_user_login(client: TestClient):
    """Попытка входа несуществующего пользователя."""
    return await client.post(
        RoutersTestData.LOGIN_URL,
        form={"username": RateLimitTestData.UNKNOWN_EMAIL, "password": "irrelevant"},
    )


async def try_register_w_incorrect_repeat_password(client: TestClient):
    """Попытка регистрации с некорректным подтверждением пароля."""
    return await client.post(
        RoutersTestData.REGISTER_URL,
        json=register_payload(repeat_password="different-password"),
    )


def client_with_ip(ip: str) -> TestClient:
    """Клиент с заданным Ip-адресом."""
    return TestClient(app, scope={"client": (ip, RateLimitTestData.CLIENT_PORT)})


async def test_error_login_is_blocked_after_limit(
    rate_limit_enabled: None, main_client: TestClient
) -> None:
    """После исчерпания лимита попыток при входе падает ошибка 429 с Retry-After"""
    # Arrange
    for _ in range(RateLimitTestData.AUTH_ATTEMPTS):
        resp = await try_unknown_user_login(main_client)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Act
    resp = await try_unknown_user_login(main_client)

    # Assert
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert (
        1 <= int(resp.headers["Retry-After"]) <= RateLimitTestData.AUTH_INTERVAL_SECONDS
    )
    assert "Повторите через" in resp.json()["detail"]


async def test_error_register_is_blocked_after_limit(
    rate_limit_enabled: None, main_client: TestClient
) -> None:
    """После исчерпания лимита попыток при регистрации падает ошибка 429 с Retry-After"""
    # Arrange
    for _ in range(RateLimitTestData.AUTH_ATTEMPTS):
        resp = await try_register_w_incorrect_repeat_password(main_client)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Act
    resp = await try_register_w_incorrect_repeat_password(main_client)

    # Assert
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert (
        1 <= int(resp.headers["Retry-After"]) <= RateLimitTestData.AUTH_INTERVAL_SECONDS
    )


async def test_login_and_register_have_separate_counters(
    rate_limit_enabled: None, main_client: TestClient
) -> None:
    """Исчерпанный лимит входа не блокирует регистрацию"""
    # Arrange
    for _ in range(RateLimitTestData.AUTH_ATTEMPTS + 1):
        await try_unknown_user_login(main_client)

    # Act
    resp = await try_register_w_incorrect_repeat_password(main_client)

    # Assert
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_concurrent_requests_do_not_exceed_limit(
    rate_limit_enabled: None, main_client: TestClient
) -> None:
    """При параллельных запросах лимит пропускает ровно заданное число попыток"""
    # Act
    responses = await asyncio.gather(
        *(
            try_unknown_user_login(main_client)
            for _ in range(RateLimitTestData.AUTH_ATTEMPTS * 4)
        )
    )

    # Assert
    statuses = [resp.status_code for resp in responses]
    assert statuses.count(status.HTTP_404_NOT_FOUND) == RateLimitTestData.AUTH_ATTEMPTS
    assert (
        statuses.count(status.HTTP_429_TOO_MANY_REQUESTS)
        == RateLimitTestData.AUTH_ATTEMPTS * 3
    )


@pytest.mark.parametrize(
    "attempt", [try_unknown_user_login, try_register_w_incorrect_repeat_password]
)
async def test_error_auth_returns_503_when_redis_is_unavailable(
    attempt, redis_unavailable: None, main_client: TestClient
) -> None:
    """Если Redis недоступен, вход и регистрация получают 503, а не обходят лимит"""
    # Act
    resp = await attempt(main_client)

    # Assert
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.parametrize(
    ("attempt", "expected_status"),
    [
        pytest.param(try_unknown_user_login, status.HTTP_404_NOT_FOUND, id="login"),
        pytest.param(
            try_register_w_incorrect_repeat_password,
            status.HTTP_400_BAD_REQUEST,
            id="register",
        ),
    ],
)
async def test_blocked_ip_does_not_block_other_ip(
    attempt, expected_status: int, rate_limit_enabled: None
) -> None:
    """Исчерпанный лимит одного IP не блокирует вход и регистрацию с другого IP"""
    # Arrange
    blocked_client = client_with_ip(RateLimitTestData.FIRST_IP)
    other_client = client_with_ip(RateLimitTestData.SECOND_IP)
    for _ in range(RateLimitTestData.AUTH_ATTEMPTS):
        await attempt(blocked_client)
    blocked = await attempt(blocked_client)

    # Act
    resp = await attempt(other_client)

    # Assert
    assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert resp.status_code == expected_status
