import pytest
from async_asgi_testclient import TestClient
from fastapi import status

from ....constants import RoutersTestData
from ....utils.auth import UserData


async def test_current_user_returns_authorized_user(
    main_client: TestClient, user_one: UserData
) -> None:
    """Текущий пользователь возвращается по cookie с токеном"""
    # Act
    resp = await main_client.get(RoutersTestData.CURRENT_USER_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["id"] == user_one.id
    assert body["email"] == user_one.email
    assert body["full_name"] == user_one.full_name


async def test_current_user_without_cookie_redirects_to_login(
    main_client: TestClient,
) -> None:
    """Без авторизации запрос текущего пользователя перенаправляет на страницу входа"""
    # Act
    resp = await main_client.get(
        RoutersTestData.CURRENT_USER_URL, allow_redirects=False
    )

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL


async def test_error_current_user_with_invalid_token(
    main_client: TestClient,
) -> None:
    """С невалидным токеном запрос текущего пользователя возвращает ошибку"""
    # Act
    resp = await main_client.get(
        RoutersTestData.CURRENT_USER_URL,
        cookies={"access_token": "not-a-jwt"},
        allow_redirects=False,
    )

    # Assert
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_all_users_contains_every_registered_user(
    main_client: TestClient, user_one: UserData, user_two: UserData
) -> None:
    """Список всех пользователей содержит каждого зарегистрированного пользователя"""
    # Act
    resp = await main_client.get(RoutersTestData.ALL_USERS_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert {user["id"] for user in resp.json()} == {user_one.id, user_two.id}


@pytest.mark.xfail(
    strict=True,
    reason="TO-DO: Поправить после того, как из ответа уберут hashed_password",
)
async def test_current_user_does_not_expose_hashed_password(
    main_client: TestClient, user_one: UserData
) -> None:
    """Ответ с текущим пользователем не содержит хеш пароля"""
    # Act
    resp = await main_client.get(RoutersTestData.CURRENT_USER_URL)

    # Assert
    assert "hashed_password" not in resp.json()


@pytest.mark.xfail(
    strict=True,
    reason="TO-DO: Поправить после того, как из ответа уберут hashed_password",
)
async def test_all_users_does_not_expose_hashed_password(
    main_client: TestClient, user_one: UserData
) -> None:
    """Список всех пользователей не содержит хеш пароля"""
    # Act
    resp = await main_client.get(RoutersTestData.ALL_USERS_URL)

    # Assert
    assert all("hashed_password" not in user for user in resp.json())
