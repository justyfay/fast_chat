from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from fast_chat.config import settings
from fast_chat.database import sessionmanager
from fast_chat.logger import get_logger
from fast_chat.exceptions import TokenNoFoundException, TokenExpiredException
from fast_chat.routers import api_router

logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Метод создаёт пул соединений с БД при старте и закрывает его при остановке."""
    sessionmanager.connect()
    yield
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
