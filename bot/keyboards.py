"""Constructores de teclados."""

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.callbacks import EquipCB, FightCB, InventoryCB
from bot.game import combat
from bot.models import Fight, Item


def main_menu() -> ReplyKeyboardMarkup:
    """Teclado persistente con las acciones del día a día."""
    rows = [
        [KeyboardButton(text=texts.BTN_DUNGEON), KeyboardButton(text=texts.BTN_PROFILE)],
        [KeyboardButton(text=texts.BTN_INVENTORY)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def inventory(items: list[Item], page: int, pages: int, user_id: int) -> InlineKeyboardMarkup:
    """Un número por objeto de la página y las flechas si hay más de una."""
    builder = InlineKeyboardBuilder()
    for index, item in enumerate(items, start=1):
        builder.button(text=str(index), callback_data=EquipCB(item_id=item.id, user_id=user_id))
    builder.adjust(4)

    arrows = InlineKeyboardBuilder()
    if page > 1:
        arrows.button(
            text=texts.BTN_PREV, callback_data=InventoryCB(page=page - 1, user_id=user_id)
        )
    if page < pages:
        arrows.button(
            text=texts.BTN_NEXT, callback_data=InventoryCB(page=page + 1, user_id=user_id)
        )
    builder.attach(arrows)
    return builder.as_markup()


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
