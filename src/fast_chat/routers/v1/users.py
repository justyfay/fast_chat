from fastapi import APIRouter, Depends
from sqlalchemy import RowMapping

from fast_chat.dependencies.auth import get_current_user
from fast_chat.dependencies.services import get_user_service
from fast_chat.schemas.user import UserSchema
from fast_chat.services.user import UserService

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
    service: UserService = Depends(get_user_service),
):
    return await service.get_all()
