"""Factorías de CallbackData; nada de strings a mano."""

from aiogram.filters.callback_data import CallbackData


class FightCB(CallbackData, prefix="f"):
    action: str  # "atk" | "potion" | "flee"
    fight_id: int
    turn: int
    user_id: int


class EquipCB(CallbackData, prefix="eq"):
    item_id: int
    user_id: int


class InventoryCB(CallbackData, prefix="inv"):
    page: int
    user_id: int


class ShopCB(CallbackData, prefix="sh"):
    action: str  # "main" | "buy" | "sell"
    page: int
    user_id: int


class SellCB(CallbackData, prefix="sl"):
    item_id: int
    page: int
    user_id: int
