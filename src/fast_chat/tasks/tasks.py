import asyncio

from aiogram import Bot

from fast_chat.config import settings
from fast_chat.tasks.celery_app import celery


async def _send_message(chat_id: int, text: str) -> None:
    bot = Bot(token=settings.bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()


@celery.task(name="send_notification_to_telegram")
def send_notification_to_telegram(chat_id: int, message: str, sender_name: str) -> None:
    message_text = f"Сообщение от пользователя {sender_name}: {message}"
    asyncio.run(_send_message(chat_id, message_text))
