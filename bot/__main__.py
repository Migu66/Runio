"""Punto de entrada: python -m bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_settings
from bot.handlers import register_all

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


async def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level.upper(), format=LOG_FORMAT)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_all(dp)

    me = await bot.get_me()
    logger.info("Arrancando como @%s", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido")
