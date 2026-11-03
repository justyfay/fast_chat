from fastapi import APIRouter, Depends, status
from sqlalchemy import RowMapping

from fast_chat.dependencies.auth import get_current_user
from fast_chat.dependencies.services import get_chat_service
from fast_chat.schemas.user import UserSchema
from fast_chat.services.chat import ChatService

conv_router = APIRouter(prefix="/conversations", tags=["Чаты"])


@conv_router.get(
    "/",
    response_model=list[UserSchema],
    description="Список собеседников, добавленных текущим пользователем в чаты.",
)
async def get_conversations(
    current_user: RowMapping = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.get_partners(current_user.id)


@conv_router.post(
    "/{recipient_id}",
    status_code=status.HTTP_201_CREATED,
    description="Добавление пользователя в список чатов.",
)
async def add_conversation(
    recipient_id: int,
    current_user: RowMapping = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    added = await service.add(current_user.id, recipient_id)
    return {"added": added, "recipient_id": recipient_id}


@conv_router.delete(
    "/{recipient_id}",
    status_code=status.HTTP_200_OK,
    description="Удалить чат из списка чатов (сообщения сохраняются).",
)
async def delete_conversation(
    recipient_id: int,
    current_user: RowMapping = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.delete(current_user.id, recipient_id)
    return {"deleted": True, "recipient_id": recipient_id}


@conv_router.get(
    "/search",
    response_model=list[UserSchema],
    description="Список пользователей, доступных для добавления в беседы (без уже добавленных).",
)
async def search_available_users(
    q: str = "",
    current_user: RowMapping = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.search_available(current_user.id, q)
