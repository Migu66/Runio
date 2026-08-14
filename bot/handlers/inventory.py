"""Mochila paginada y equipamiento."""

import logging
from dataclasses import replace

import aiosqlite
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import keyboards, texts
from bot.callbacks import EquipCB, InventoryCB
from bot.db import transaction
from bot.game import balance
from bot.models import SLOT_AMULET, SLOT_ARMOR, SLOT_WEAPON, Player
from bot.repo import items

logger = logging.getLogger(__name__)
router = Router(name="inventory")

_SLOT_FIELD = {SLOT_WEAPON: "weapon_id", SLOT_ARMOR: "armor_id", SLOT_AMULET: "amulet_id"}


async def _render(
    db: aiosqlite.Connection, player: Player, page: int
) -> tuple[str, InlineKeyboardMarkup | None]:
    total = await items.count_owned(db, player.user_id)
    if total == 0:
        return texts.INVENTORY_EMPTY, None

    size = balance.INVENTORY_PAGE_SIZE
    pages = max(1, -(-total // size))
    page = max(1, min(page, pages))
    listado = await items.page(db, player.user_id, size, (page - 1) * size)
    equipped = {i for i in (player.weapon_id, player.armor_id, player.amulet_id) if i}
    return (
        texts.render_inventory(listado, page, pages, total, equipped),
        keyboards.inventory(listado, page, pages, player.user_id),
    )


async def _edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if not isinstance(cb.message, Message):
        return
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.info("No se pudo refrescar la mochila: %s", exc)


@router.message(Command("equipo"))
@router.message(F.text == texts.BTN_INVENTORY)
async def cmd_inventory(message: Message, db: aiosqlite.Connection, player: Player) -> None:
    text, markup = await _render(db, player, page=1)
    await message.answer(text, reply_markup=markup)


@router.callback_query(InventoryCB.filter())
async def on_page(
    cb: CallbackQuery, callback_data: InventoryCB, db: aiosqlite.Connection, player: Player
) -> None:
    if cb.from_user.id != callback_data.user_id:
        await cb.answer(texts.NOT_YOURS, show_alert=True)
        return
    text, markup = await _render(db, player, callback_data.page)
    await _edit(cb, text, markup)
    await cb.answer()


@router.callback_query(EquipCB.filter())
async def on_equip(
    cb: CallbackQuery, callback_data: EquipCB, db: aiosqlite.Connection, player: Player
) -> None:
    if cb.from_user.id != callback_data.user_id:
        await cb.answer(texts.NOT_YOURS, show_alert=True)
        return

    item = await items.get(db, callback_data.item_id)
    if item is None or item.owner_id != player.user_id:
        await cb.answer(texts.ITEM_GONE, show_alert=True)
        return

    async with transaction(db):
        await items.equip(db, player.user_id, item)
    await cb.answer(texts.EQUIPPED_OK.format(item=item.name))

    # Se refresca la página en la que estaba el objeto, no la primera.
    equipado = replace(player, **{_SLOT_FIELD[item.slot]: item.id})
    posicion = await items.position(db, player.user_id, item.id)
    text, markup = await _render(db, equipado, posicion // balance.INVENTORY_PAGE_SIZE + 1)
    await _edit(cb, text, markup)
