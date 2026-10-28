from fastapi import APIRouter, Request, Depends
from sqlalchemy import RowMapping
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from fast_chat.dependencies.auth import get_current_user
from fast_chat.utils.static_version import get_static_version

pages_router = APIRouter(prefix="", tags=["Страницы"])
templates = Jinja2Templates(directory="src/fast_chat/templates")
templates.env.globals["static_version"] = get_static_version


@pages_router.get("/", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    current_user: RowMapping = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "chat.html", {"request": request, "current_user": current_user}
    )


@pages_router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})
