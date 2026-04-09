from fastapi import APIRouter, Depends
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from src.fast_chat.dao.message import MessageDAO
from src.fast_chat.dependencies.auth import get_current_user
from src.fast_chat.dependencies.database import get_session
from src.fast_chat.schemas.message import MessageCreate, MessageRead

msg_router = APIRouter(prefix="/messages", tags=["Сообщения"])


@msg_router.post("/send", response_model=MessageCreate)
async def send_message(
    message: MessageCreate,
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await MessageDAO.add(
        db_session=session,
        sender_id=current_user.id,
        body=message.body,
        recipient_id=message.recipient_id,
    )

    return {
        "recipient_id": message.recipient_id,
        "body": message.body,
        "status": "ok",
        "msg": "Message saved!",
    }


@msg_router.get("/{user_id}", response_model=list[MessageRead])
async def get_messages(
    user_id: int,
    current_user: RowMapping = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return (
        await MessageDAO.get_messages_between_users(
            db_session=session, user_id_1=user_id, user_id_2=current_user.id
        )
        or []
    )
