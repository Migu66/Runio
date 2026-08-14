"""Constructores de teclados."""

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.callbacks import FightCB
from bot.game import combat
from bot.models import Fight


def main_menu() -> ReplyKeyboardMarkup:
    """Teclado persistente con las acciones del día a día."""
    rows = [[KeyboardButton(text=texts.BTN_DUNGEON), KeyboardButton(text=texts.BTN_PROFILE)]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def fight(fight_state: Fight, potions: int) -> InlineKeyboardMarkup:
    """Botones del turno actual: el `turn` que llevan dentro es lo que da la idempotencia."""

    def action(name: str) -> FightCB:
        return FightCB(
            action=name,
            fight_id=fight_state.id,
            turn=fight_state.turn,
            user_id=fight_state.user_id,
        )

    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_ATTACK, callback_data=action(combat.ACTION_ATTACK))
    if potions > 0:
        builder.button(
            text=texts.BTN_POTION.format(n=potions),
            callback_data=action(combat.ACTION_POTION),
        )
    builder.button(text=texts.BTN_FLEE, callback_data=action(combat.ACTION_FLEE))
    builder.adjust(3)
    return builder.as_markup()
