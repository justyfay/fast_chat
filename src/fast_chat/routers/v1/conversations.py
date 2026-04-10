from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from src.fast_chat.dao.conversation import ConversationDAO
from src.fast_chat.dao.user import UserDAO
from src.fast_chat.dependencies.auth import get_current_user
from src.fast_chat.dependencies.database import get_session

conv_router = APIRouter(prefix="/conversations", tags=["Беседы"])


@conv_router.get(
    "/",
    description="Список собеседников, добавленных текущим пользователем в беседы.",
)
async def get_conversations(
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ConversationDAO.get_partners(db_session=session, user_id=current_user.id)


@conv_router.post(
    "/{recipient_id}",
    status_code=status.HTTP_201_CREATED,
    description="Добавление пользователя в список бесед.",
)
async def add_conversation(
    recipient_id: int,
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if recipient_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add yourself")

    recipient = await UserDAO.find_one_or_none(db_session=session, id=recipient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    added = await ConversationDAO.add_conversation(
        db_session=session, user_id=current_user.id, recipient_id=recipient_id
    )
    return {"added": added, "recipient_id": recipient_id}


@conv_router.delete(
    "/{recipient_id}",
    status_code=status.HTTP_200_OK,
    description="Удалить чат из списка бесед (сообщения сохраняются).",
)
async def delete_conversation(
    recipient_id: int,
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    deleted = await ConversationDAO.delete_conversation(
        db_session=session, user_id=current_user.id, recipient_id=recipient_id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"deleted": True, "recipient_id": recipient_id}


@conv_router.get(
    "/search",
    description="Список пользователей, доступных для добавления в беседы (без уже добавленных).",
)
async def search_available_users(
    q: str = "",
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    users = await ConversationDAO.get_available_users(
        db_session=session, user_id=current_user.id
    )
    if q:
        q_lower = q.lower()
        users = [u for u in users if q_lower in u["full_name"].lower()]
    return users
