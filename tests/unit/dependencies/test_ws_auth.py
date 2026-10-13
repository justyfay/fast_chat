from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocketException, status
from pytest_mock import MockerFixture

from fast_chat.dependencies.auth import get_ws_user
from fast_chat.utils.auth import create_access_token

USERNAME = "alisson@example.com"


@pytest.fixture
def find_user(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch(
        "fast_chat.dependencies.auth.UserDAO.find_one_or_none",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(id=1, username=USERNAME),
    )


def make_websocket(token: str | None) -> MagicMock:
    websocket = MagicMock()
    websocket.cookies = {"access_token": token} if token else {}
    return websocket


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(None, id="no-cookie"),
        pytest.param("not-a-jwt", id="garbage"),
        pytest.param(
            create_access_token({"sub": USERNAME}, timedelta(minutes=-1)), id="expired"
        ),
        pytest.param(create_access_token({}), id="no-subject"),
    ],
)
async def test_error_ws_user_with_bad_token(
    token: str | None, find_user: AsyncMock
) -> None:
    """Невалидный токен отдает код 1008."""
    # Act
    with pytest.raises(WebSocketException) as exc_info:
        await get_ws_user(make_websocket(token), session=MagicMock())

    # Assert
    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    find_user.assert_not_called()


async def test_error_ws_user_when_user_not_found(find_user: AsyncMock) -> None:
    """Токен несуществующего пользователя отдает код 1008."""
    # Arrange
    find_user.return_value = None
    token = create_access_token({"sub": USERNAME})

    # Act
    with pytest.raises(WebSocketException) as exc_info:
        await get_ws_user(make_websocket(token), session=MagicMock())

    # Assert
    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION


async def test_ws_user_returns_user_name_by_valid_token(find_user: AsyncMock) -> None:
    """Валидный токен возвращает имя пользователя."""
    # Arrange
    token = create_access_token({"sub": USERNAME})

    # Act
    user = await get_ws_user(make_websocket(token), session=MagicMock())

    # Assert
    assert user.username == USERNAME
