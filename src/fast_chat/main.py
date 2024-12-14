from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from config import settings
from logger import get_logger
from src.fast_chat.exceptions import TokenNoFoundException, TokenExpiredException
from src.fast_chat.routers import api_router

logger = get_logger()


app: FastAPI = FastAPI(
    title="FastChat", summary="Сервис обмена мгновенными сообщениями.", version="1.0.0"
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


app.include_router(api_router)
