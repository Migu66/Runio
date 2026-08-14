from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot import texts
from bot.game import formulas
from bot.models import SLOTS, Item, Player

router = Router(name="profile")


@router.message(Command("perfil"))
@router.message(F.text == texts.BTN_PROFILE)
async def cmd_profile(message: Message, player: Player) -> None:
    equipped: dict[str, Item | None] = dict.fromkeys(SLOTS)
    stats = formulas.effective_stats(player, [])
    await message.answer(texts.render_profile(player, stats, equipped))
