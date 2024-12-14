from fastapi import APIRouter, Request, Depends
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from src.fast_chat.dependencies.auth import get_current_user
from src.fast_chat.dependencies.database import get_session

pages_router = APIRouter(prefix="", tags=["Страницы"])
templates = Jinja2Templates(directory="src/fast_chat/templates")


@pages_router.get("/", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return templates.TemplateResponse(
        "chat.html", {"request": request, "current_user": current_user}
    )


@pages_router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})
