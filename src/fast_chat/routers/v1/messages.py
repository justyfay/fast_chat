from fastapi import APIRouter, Depends
from sqlalchemy import RowMapping

from fast_chat.dependencies.auth import get_current_user
from fast_chat.dependencies.services import get_message_service
from fast_chat.schemas.message import MessageCreate, MessageRead
from fast_chat.services.message import MessageService

msg_router = APIRouter(prefix="/messages", tags=["Сообщения"])


@msg_router.post("/send", response_model=MessageCreate)
async def send_message(
    message: MessageCreate,
    current_user: RowMapping = Depends(get_current_user),
    service: MessageService = Depends(get_message_service),
):
    await service.send(current_user.id, message.recipient_id, message.body)

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
    service: MessageService = Depends(get_message_service),
):
    return await service.get_history(current_user.id, user_id)
