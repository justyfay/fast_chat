from dataclasses import dataclass

from async_asgi_testclient import TestClient
from fastapi import status

from ..constants import RoutersTestData, UsersTestData


@dataclass(frozen=True)
class UserData:
    id: int
    email: str
    full_name: str
    password: str


def register_payload(
    email: str = "alisson@example.com",
    full_name: str = "Alisson Becker",
    password: str = UsersTestData.DEFAULT_PASSWORD,
    repeat_password: str | None = None,
    telegram_unic_code: str = "",
) -> dict:
    return {
        "email": email,
        "full_name": full_name,
        "password": password,
        "repeat_password": password if repeat_password is None else repeat_password,
        "telegram_unic_code": telegram_unic_code,
    }


async def register_user(client: TestClient, **kwargs) -> UserData:
    payload = register_payload(**kwargs)
    resp = await client.post(RoutersTestData.REGISTER_URL, json=payload)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    return UserData(
        id=resp.json()["id"],
        email=payload["email"],
        full_name=payload["full_name"],
        password=payload["password"],
    )


async def login_user(client: TestClient, email: str, password: str) -> str:
    """Выполняет вход и возвращает выданный токен (он же сохраняется в cookie клиента)."""
    resp = await client.post(
        RoutersTestData.LOGIN_URL, form={"username": email, "password": password}
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    return resp.json()["access_token"]


async def register_and_login(client: TestClient, **kwargs) -> UserData:
    user = await register_user(client, **kwargs)
    await login_user(client, user.email, user.password)
    return user
