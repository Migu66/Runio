import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.game import formulas
from bot.models import Player
from bot.repo import items

router = Router(name="profile")


@router.message(Command("perfil"))
@router.message(F.text == texts.BTN_PROFILE)
async def cmd_profile(message: Message, db: aiosqlite.Connection, player: Player, now: int) -> None:
    equipped = await items.get_equipped(db, player)
    stats = formulas.effective_stats(player, [i for i in equipped.values() if i is not None])
    seconds = formulas.seconds_to_next_energy(player.energy, player.energy_ts, now)
    hint = "" if seconds == 0 else texts.ENERGY_HINT.format(time=texts.format_duration(seconds))
    await message.answer(texts.render_profile(player, stats, equipped, hint))
