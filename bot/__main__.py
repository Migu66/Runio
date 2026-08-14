"""Punto de entrada: python -m bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot import db as database
from bot.config import load_settings
from bot.handlers import register_all
from bot.middlewares import EnsurePlayerMiddleware

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level.upper(), format=LOG_FORMAT)

    db = await database.connect(settings.db_path)
    await database.run_migrations(db)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["db"] = db
    dp.message.middleware(EnsurePlayerMiddleware())
    dp.callback_query.middleware(EnsurePlayerMiddleware())
    register_all(dp)

    try:
        me = await bot.get_me()
        logger.info("Arrancando como @%s", me.username)
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido")
