import asyncio

from bot.main import get_bot
from src.fast_chat.tasks.celery_app import celery


@celery.task(name="send_notification_to_telegram")
def send_notification_to_telegram(chat_id: int, message: str, sender_name: str) -> None:
    message_text = f"Сообщение от пользователя {sender_name}: {message}"
    asyncio.run(get_bot().send_message(chat_id=chat_id, text=message_text))
