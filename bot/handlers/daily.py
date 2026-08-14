"""Recompensa diaria."""

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.game import balance
from bot.models import Player
from bot.repo import players

router = Router(name="daily")


@router.message(Command("diario"))
@router.message(F.text == texts.BTN_DAILY)
async def cmd_daily(message: Message, db: aiosqlite.Connection, player: Player, now: int) -> None:
    premiado = await players.claim_daily(db, player.user_id, now)
    if premiado is None:
        falta = balance.DAILY_COOLDOWN_SECONDS - (now - player.last_daily)
        await message.answer(texts.DAILY_WAIT.format(time=texts.format_duration(falta)))
        return
    await message.answer(
        texts.DAILY_OK.format(
            gold=balance.DAILY_GOLD,
            potions=balance.DAILY_POTIONS,
            hours=balance.DAILY_COOLDOWN_SECONDS // 3600,
        )
    )
