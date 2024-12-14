from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, Depends
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from src.fast_chat.dao.user import UserDAO
from src.fast_chat.dao.message import MessageDAO

from logger import get_logger
from src.fast_chat.dependencies.database import get_session
from src.fast_chat.schemas.message import MessageRead
from src.fast_chat.tasks.tasks import send_notification_to_telegram

logger = get_logger()
ws_router = APIRouter(prefix="/ws", tags=["Сокеты"])
active_connections: dict[int, Any] = defaultdict(int)


@ws_router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: int, session: AsyncSession = Depends(get_session)
):
    await websocket.accept()
    active_connections[user_id] = websocket
    logger.debug(f"Активные подключения: {active_connections}")

    try:
        while True:
            data = await websocket.receive_json()
            try:
                append_msg: RowMapping = await MessageDAO.add(
                    db_session=session,
                    sender_id=int(data["sender_id"]),
                    body=data["body"],
                    recipient_id=int(data["recipient_id"]),
                )
                appended_msg: RowMapping = await MessageDAO.find_one_or_none(
                    db_session=session, id=append_msg["id"]
                )
                validated_msg = MessageRead.model_validate(appended_msg)
                logger.debug(f"Получено сообщение от: '{data['sender_id']}'. ")

            except Exception as e:
                logger.debug(f"Ошибка во время сохранения сообщения в БД: '{e}'.")
                break

            if int(data["recipient_id"]) in active_connections:
                websocket_recipient: WebSocket = active_connections[
                    int(data["recipient_id"])
                ]
                logger.debug(
                    f"Веб-сокет получателя: '{data['recipient_id']}' найден: '{websocket}'."
                )

                await websocket_recipient.send_json(validated_msg.model_dump())
                logger.debug(
                    f"Сообщение '{appended_msg}' отправлено пользователю: '{data['recipient_id']}'",
                )

            else:
                recipient_user: RowMapping = await UserDAO.find_one_or_none(
                    db_session=session, id=int(data["recipient_id"])
                )
                sender_user: RowMapping = await UserDAO.find_one_or_none(
                    db_session=session, id=int(data["sender_id"])
                )

                if recipient_user.telegram_unic_code is not None:
                    logger.debug(
                        f"Пользователь '{recipient_user.id} оффлайн. Отправляем сообщение в Телегам.'",
                    )
                    send_notification_to_telegram.delay(
                        chat_id=recipient_user.telegram_unic_code,
                        message=validated_msg.body,
                        sender_name=sender_user.full_name,
                    )

            if int(data["sender_id"]) in active_connections:
                websocket_recipient: WebSocket = active_connections[
                    int(data["sender_id"])
                ]
                logger.debug(
                    f"Веб-сокет отправителя: '{data['sender_id']}' найден: '{websocket}'."
                )

                await websocket_recipient.send_json(validated_msg.model_dump())
                logger.debug(
                    f"Сообщение '{appended_msg}' отправлено пользователю: '{data['sender_id']}'",
                )

    except WebSocketDisconnect:
        logger.debug(f"User: '{user_id}' отключился от веб-сокета.")
        if user_id in active_connections:
            del active_connections[user_id]

    except Exception:  # noqa
        logger.exception("Неизвестная ошибка в подключении по веб-сокету.")
        if user_id in active_connections:
            del active_connections[user_id]
