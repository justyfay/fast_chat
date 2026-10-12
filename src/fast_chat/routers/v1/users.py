from fastapi import APIRouter, Depends
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from fast_chat.dao.user import UserDAO
from fast_chat.dependencies.auth import get_current_user
from fast_chat.dependencies.database import get_session
from fast_chat.schemas.user import UserSchema

user_router = APIRouter(prefix="/users", tags=["Пользователи"])


@user_router.get("/current_user", response_model=UserSchema)
async def get_user(current_user: RowMapping = Depends(get_current_user)):
    return current_user


@user_router.get(
    "/all",
    response_model=list[UserSchema],
    description="Все пользователи (кроме текущего).",
)
async def read_all_users(
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await UserDAO.find_all(db_session=session)
