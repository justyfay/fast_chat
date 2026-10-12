from async_asgi_testclient import TestClient
from fastapi import status
from jose import jwt

from fast_chat.config import settings
from ....constants import RoutersTestData, UsersTestData
from ....utils.auth import UserData, register_user


async def test_login_success_w_token_and_sets_cookie(
    main_client: TestClient,
) -> None:
    """Успешный вход возвращает токен и устанавливает cookie"""
    # Arrange
    user = await register_user(main_client)

    # Act
    resp = await main_client.post(
        RoutersTestData.LOGIN_URL,
        form={"username": user.email, "password": user.password},
    )

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    token = resp.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == user.email
    set_cookie = resp.headers["set-cookie"]
    assert f"access_token={token}" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


async def test_login_wrong_password_not_found(main_client: TestClient) -> None:
    """При указании неправильного пароля вход не выполняется"""
    # Arrange
    user = await register_user(main_client)

    # Act
    resp = await main_client.post(
        RoutersTestData.LOGIN_URL,
        form={"username": user.email, "password": "wrong-password"},
    )

    # Assert
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "set-cookie" not in resp.headers


async def test_login_unknown_user_not_found(main_client: TestClient) -> None:
    """Вход несуществующего пользователя не выполняется"""
    # Act
    resp = await main_client.post(
        RoutersTestData.LOGIN_URL,
        form={
            "username": "ghost@example.com",
            "password": UsersTestData.DEFAULT_PASSWORD,
        },
    )

    # Assert
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_login_cookie_gives_access_to_protected_endpoint(
    main_client: TestClient, user_one: UserData
) -> None:
    """Cookie, полученный при входе, даёт доступ к защищённому эндпоинту"""
    # Act
    resp = await main_client.get(RoutersTestData.CURRENT_USER_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["email"] == user_one.email


async def test_logout_deletes_access_token_cookie(
    main_client: TestClient, user_one: UserData
) -> None:
    """Выход из системы удаляет cookie с токеном"""
    # Act
    resp = await main_client.post(RoutersTestData.LOGOUT_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"message": "Пользователь успешно вышел из системы"}
    set_cookie = resp.headers["set-cookie"]
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie
