"""Los diez mejores y tu puesto."""

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.game import balance
from bot.models import Player
from bot.repo import players

router = Router(name="ranking")


@router.message(Command("ranking"))
@router.message(F.text == texts.BTN_RANKING)
async def cmd_ranking(message: Message, db: aiosqlite.Connection, player: Player) -> None:
    leaders = await players.top(db, balance.RANKING_SIZE)
    rank = await players.rank_of(db, player)
    await message.answer(texts.render_ranking(leaders, player, rank))
