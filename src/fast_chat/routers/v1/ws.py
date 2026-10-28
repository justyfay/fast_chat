from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketException, Depends, status
from sqlalchemy import RowMapping
from starlette.websockets import WebSocketDisconnect

from fast_chat.dependencies.auth import get_ws_user

from fast_chat.logger import get_logger
from fast_chat.dependencies.services import ConnectionServices, get_connection_services
from fast_chat.tasks.tasks import send_notification_to_telegram

logger = get_logger()
ws_router = APIRouter(prefix="/ws", tags=["Сокеты"])
active_connections: dict[int, Any] = defaultdict(int)


@ws_router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    current_user: RowMapping = Depends(get_ws_user),
    services: ConnectionServices = Depends(get_connection_services),
):
    if user_id != current_user.id:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    await websocket.accept()
    sender_id = current_user.id
    active_connections[user_id] = websocket
    logger.debug(f"Активные подключения: {list(active_connections.keys())}")

    try:
        while True:
            data = await websocket.receive_json()
            try:
                recipient_id = int(data["recipient_id"])
                async with services.message_service() as message_service:
                    validated_msg = await message_service.send(
                        sender_id, recipient_id, data["body"]
                    )
                logger.debug(
                    f"Получено сообщение от: '{sender_id}', id={validated_msg.id}."
                )

            except Exception as e:
                logger.debug(f"Ошибка во время сохранения сообщения в БД: '{e}'.")
                break

            if recipient_id in active_connections:
                websocket_recipient: WebSocket = active_connections[recipient_id]
                logger.debug(
                    f"Веб-сокет получателя: '{data['recipient_id']}' найден: '{websocket}'."
                )

                await websocket_recipient.send_json(validated_msg.model_dump())
                logger.debug(
                    f"Сообщение id={validated_msg.id} отправлено пользователю: '{data['recipient_id']}'",
                )

            else:
                async with services.user_service() as user_service:
                    recipient_user: RowMapping = await user_service.get_by_id(
                        recipient_id
                    )

                if recipient_user.telegram_unic_code is not None:
                    logger.debug(
                        f"Пользователь '{recipient_user.id}' оффлайн. Отправляем сообщение в Телеграм.",
                    )
                    send_notification_to_telegram.delay(
                        chat_id=recipient_user.telegram_unic_code,
                        message=validated_msg.body,
                        sender_name=current_user.full_name,
                    )

            if sender_id in active_connections:
                websocket_recipient: WebSocket = active_connections[sender_id]
                logger.debug(
                    f"Веб-сокет отправителя: '{sender_id}' найден: '{websocket}'."
                )

                await websocket_recipient.send_json(validated_msg.model_dump())
                logger.debug(
                    f"Сообщение id={validated_msg.id} отправлено пользователю: '{sender_id}'",
                )

    except WebSocketDisconnect:
        logger.debug(f"User: '{user_id}' отключился от веб-сокета.")
        if user_id in active_connections:
            del active_connections[user_id]

    except Exception:  # noqa
        logger.exception("Неизвестная ошибка в подключении по веб-сокету.")
        if user_id in active_connections:
            del active_connections[user_id]
