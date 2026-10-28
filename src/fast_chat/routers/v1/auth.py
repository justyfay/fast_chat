from fastapi import APIRouter, Request, Response, Depends
from fastapi.security import OAuth2PasswordRequestForm

from fast_chat.constants import AuthData
from fast_chat.dependencies.rate_limit import (
    login_rate_limit,
    refresh_rate_limit,
    register_rate_limit,
)
from fast_chat.dependencies.services import get_auth_service
from fast_chat.schemas.user import UserRegisterSchema, UserLoginResponseSchema
from fast_chat.services.auth import AuthService
from fast_chat.utils.refresh_tokens import refresh_ttl

auth_router = APIRouter(prefix="/auth", tags=["Авторизация"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Обе cookie живут до истечения срока жизни refresh-токена,
    просроченный access обновляется через `/auth/refresh`.

    :param response: Ответ сервера, в который записываются cookie
    :param access_token: Access-токен (JWT)
    :param refresh_token: Refresh-токен в открытом виде
    """
    max_age = refresh_ttl()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=max_age,
    )
    response.set_cookie(
        key=AuthData.REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=max_age,
        path=AuthData.REFRESH_COOKIE_PATH,
    )


@auth_router.post("/register", dependencies=[Depends(register_rate_limit)])
async def register_user(
    user: UserRegisterSchema, service: AuthService = Depends(get_auth_service)
):
    return await service.register(user)


@auth_router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login_user(
    response: Response,
    user: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> UserLoginResponseSchema:
    access_token, refresh_token = await service.login(user.username, user.password)
    set_auth_cookies(response, access_token, refresh_token)
    return UserLoginResponseSchema(access_token=access_token)


@auth_router.post(
    "/refresh",
    dependencies=[Depends(refresh_rate_limit)],
    description="Обновляет сессию по refresh-токену из cookie: выдаёт новую пару токенов.",
)
async def refresh_session(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> UserLoginResponseSchema:
    access_token, refresh_token = await service.refresh(
        request.cookies.get(AuthData.REFRESH_COOKIE)
    )
    set_auth_cookies(response, access_token, refresh_token)
    return UserLoginResponseSchema(access_token=access_token)


@auth_router.post("/logout")
async def logout_user(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    await service.logout(
        request.cookies.get("access_token"),
        request.cookies.get(AuthData.REFRESH_COOKIE),
    )
    response.delete_cookie(key="access_token")
    response.delete_cookie(
        key=AuthData.REFRESH_COOKIE, path=AuthData.REFRESH_COOKIE_PATH
    )
    return {"message": "Пользователь успешно вышел из системы"}
