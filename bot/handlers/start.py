from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import texts

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.WELCOME)
