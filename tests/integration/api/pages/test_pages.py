import html

from async_asgi_testclient import TestClient
from fastapi import status

from ....constants import RoutersTestData, XssTestData
from ....utils.auth import UserData, register_and_login


async def test_login_page_is_available_without_authorization(
    main_client: TestClient,
) -> None:
    """Страница входа доступна без авторизации"""
    # Act
    resp = await main_client.get(RoutersTestData.LOGIN_PAGE_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"]


async def test_chat_page_without_cookie_redirects_to_login(
    main_client: TestClient,
) -> None:
    """Без авторизации страница чата перенаправляет на страницу входа"""
    # Act
    resp = await main_client.get(RoutersTestData.CHAT_PAGE_URL, allow_redirects=False)

    # Assert
    assert resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert resp.headers["location"] == RoutersTestData.LOGIN_PAGE_URL


async def test_chat_page_is_available_for_authorized_user(
    main_client: TestClient, user_one: UserData
) -> None:
    """Авторизованному пользователю доступна страница чата"""
    # Act
    resp = await main_client.get(RoutersTestData.CHAT_PAGE_URL)

    # Assert
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"]


async def test_chat_page_escapes_full_name(other_client: TestClient) -> None:
    """Имя пользователя с HTML-разметкой выводится на странице чата экранированным"""
    # Arrange
    await register_and_login(
        other_client, email=XssTestData.EMAIL, full_name=XssTestData.PAYLOAD
    )

    # Act
    resp = await other_client.get(RoutersTestData.CHAT_PAGE_URL)

    # Assert
    assert XssTestData.PAYLOAD not in resp.text
    assert html.escape(XssTestData.PAYLOAD) in resp.text
