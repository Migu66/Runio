"""Comprar pociones y vender lo que no llevas puesto."""

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import keyboards, texts
from bot.callbacks import SellCB, ShopCB
from bot.db import transaction
from bot.game import balance, loot
from bot.models import Player
from bot.repo import items, players

logger = logging.getLogger(__name__)
router = Router(name="shop")


async def _sell_view(
    db: aiosqlite.Connection, player: Player, page: int
) -> tuple[str, InlineKeyboardMarkup]:
    total = await items.count_sellable(db, player)
    if total == 0:
        return texts.SHOP_SELL_EMPTY, keyboards.shop_sell([], 1, 1, player.user_id)

    size = balance.INVENTORY_PAGE_SIZE
    pages = max(1, -(-total // size))
    page = max(1, min(page, pages))
    listado = await items.sellable_page(db, player, size, (page - 1) * size)
    return (
        texts.render_sell_list(listado, page, pages, total),
        keyboards.shop_sell(listado, page, pages, player.user_id),
    )


async def _edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if not isinstance(cb.message, Message):
        return
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            logger.info("No se pudo refrescar la tienda: %s", exc)


@router.message(Command("tienda"))
@router.message(F.text == texts.BTN_SHOP)
async def cmd_shop(message: Message, player: Player) -> None:
    await message.answer(
        texts.render_shop(player), reply_markup=keyboards.shop_main(player.user_id)
    )


@router.callback_query(ShopCB.filter())
async def on_shop(
    cb: CallbackQuery, callback_data: ShopCB, db: aiosqlite.Connection, player: Player
) -> None:
    if cb.from_user.id != callback_data.user_id:
        await cb.answer(texts.NOT_YOURS, show_alert=True)
        return

    if callback_data.action == "sell":
        text, markup = await _sell_view(db, player, callback_data.page)
        await _edit(cb, text, markup)
        await cb.answer()
        return

    if callback_data.action == "buy":
        comprado = False
        async with transaction(db):
            current = await players.get(db, player.user_id)
            if current is not None and current.gold >= balance.POTION_PRICE:
                await players.set_purse(
                    db,
                    current.user_id,
                    current.gold - balance.POTION_PRICE,
                    current.potions + 1,
                )
                gold = current.gold - balance.POTION_PRICE
                comprado = True
            else:
                gold = current.gold if current is not None else 0
        if not comprado:
            await cb.answer(
                texts.NOT_ENOUGH_GOLD.format(price=balance.POTION_PRICE, gold=gold),
                show_alert=True,
            )
            return
        await cb.answer(texts.BOUGHT.format(gold=texts.number(gold)))
        refreshed = await players.get(db, player.user_id)
        if refreshed is not None:
            await _edit(cb, texts.render_shop(refreshed), keyboards.shop_main(player.user_id))
        return

    refreshed = await players.get(db, player.user_id)
    if refreshed is not None:
        await _edit(cb, texts.render_shop(refreshed), keyboards.shop_main(player.user_id))
    await cb.answer()


@router.callback_query(SellCB.filter())
async def on_sell(
    cb: CallbackQuery, callback_data: SellCB, db: aiosqlite.Connection, player: Player
) -> None:
    if cb.from_user.id != callback_data.user_id:
        await cb.answer(texts.NOT_YOURS, show_alert=True)
        return

    item = await items.get(db, callback_data.item_id)
    if item is None or item.owner_id != player.user_id:
        await cb.answer(texts.ITEM_GONE, show_alert=True)
        return

    price = loot.sell_price(item.item_level, item.rarity)
    problema: str | None = None
    async with transaction(db):
        current = await players.get(db, player.user_id)
        sigue = await items.get(db, item.id)
        if current is None or sigue is None:
            problema = texts.ITEM_GONE
        elif item.id in (current.weapon_id, current.armor_id, current.amulet_id):
            problema = texts.CANNOT_SELL_EQUIPPED
        else:
            await items.delete(db, item.id)
            await players.set_purse(db, current.user_id, current.gold + price, current.potions)

    if problema is not None:
        await cb.answer(problema, show_alert=True)
        return

    await cb.answer(texts.SOLD.format(price=texts.number(price)))
    refreshed = await players.get(db, player.user_id)
    if refreshed is not None:
        text, markup = await _sell_view(db, refreshed, callback_data.page)
        await _edit(cb, text, markup)
