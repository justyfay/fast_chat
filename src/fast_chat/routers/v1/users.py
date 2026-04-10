from fastapi import APIRouter, Depends
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from src.fast_chat.dao.user import UserDAO
from src.fast_chat.dependencies.auth import get_current_user
from src.fast_chat.dependencies.database import get_session

user_router = APIRouter(prefix="/users", tags=["Пользователи"])


@user_router.get("/current_user")
async def get_user(current_user: RowMapping = Depends(get_current_user)):
    return current_user


@user_router.get("/all", description="Все пользователи (кроме текущего).")
async def read_all_users(
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await UserDAO.find_all(db_session=session)
