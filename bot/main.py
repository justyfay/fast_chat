import asyncio
import logging
import os

from aiogram import Bot, types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

telegram_bot: Bot = Bot(token=os.getenv("BOT_TOKEN"))
storage: MemoryStorage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)


@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    welcome_message: str = (
        f"\U0001f44b Привет, {message.from_user.first_name}!"
        f"\n\nТвой уникальный код: *{message.from_user.id}*"
        f"\n\nИспользуй его при регистрации на сайте *FastChat*."
        f"\nБлагодаря ему, мы сможем информировать тебя о пропущенных сообщениях. \U0001f64c"
    )
    await message.reply(welcome_message, parse_mode="Markdown")


@dp.message(Command(commands=["help"]))
async def cmd_help(message: types.Message, state: FSMContext) -> None:
    help_message: str = (
        "\u27a1\ufe0f Воспользуйся командой /start, чтобы получить свой уникальный код."
    )
    await message.reply(help_message, parse_mode="Markdown")


async def main() -> None:
    try:
        await dp.start_polling(telegram_bot, close_bot_session=True)
    except Exception as e:
        logging.exception(f"Неожиданная ошибка при запуске бота: '{e}'")


if __name__ == "__main__":
    asyncio.run(main())
