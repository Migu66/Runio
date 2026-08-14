import time

import aiosqlite
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import keyboards, texts
from bot.repo import players

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, db: aiosqlite.Connection) -> None:
    user = message.from_user
    if user is None:
        return
    player, created = await players.get_or_create(db, user.id, user.first_name, int(time.time()))
    template = texts.WELCOME if created else texts.WELCOME_BACK
    await message.answer(
        template.format(name=texts.escape(player.name)),
        reply_markup=keyboards.main_menu(),
    )
