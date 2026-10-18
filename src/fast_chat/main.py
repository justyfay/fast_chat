from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from fast_chat.config import settings
from fast_chat.database import sessionmanager
from fast_chat.redis_client import redis_manager
from fast_chat.logger import get_logger
from fast_chat.exceptions import TokenNoFoundException, TokenExpiredException
from fast_chat.routers import api_router

logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Метод создаёт пулы соединений с Postgres и Redis при старте и закрывает их при остановке."""
    if not settings.password_policy_strict:
        logger.warning(
            "Политика 'Требоания к паролю' выключена: пароли не проверяются на длину и список распространённых. "
            "Допустимо только для локальной разработки."
        )
    sessionmanager.connect()
    redis_manager.connect()
    yield
    await redis_manager.close()
    await sessionmanager.close()


app: FastAPI = FastAPI(
    title="FastChat",
    summary="Сервис обмена мгновенными сообщениями.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    middleware_class=CORSMiddleware,  # noqa
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=[
        "Content-Type",
        "Set-Cookie",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Origin",
        "Authorization",
    ],
)


# Обработчик для TokenExpiredException
@app.exception_handler(TokenExpiredException)
async def token_expired_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/v1/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return RedirectResponse(url="/login")


# Обработчик для TokenNoFound
@app.exception_handler(TokenNoFoundException)
async def token_no_found_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")


app.mount(
    "/static",
    StaticFiles(directory="src/fast_chat/templates/static"),
    name="static",
)

app.include_router(api_router)
