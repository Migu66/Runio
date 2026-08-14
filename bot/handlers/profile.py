from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.game import formulas
from bot.models import SLOTS, Item, Player

router = Router(name="profile")


@router.message(Command("perfil"))
@router.message(F.text == texts.BTN_PROFILE)
async def cmd_profile(message: Message, player: Player, now: int) -> None:
    equipped: dict[str, Item | None] = dict.fromkeys(SLOTS)
    stats = formulas.effective_stats(player, [])
    seconds = formulas.seconds_to_next_energy(player.energy, player.energy_ts, now)
    hint = "" if seconds == 0 else texts.ENERGY_HINT.format(time=texts.format_duration(seconds))
    await message.answer(texts.render_profile(player, stats, equipped, hint))
