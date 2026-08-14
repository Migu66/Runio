"""Factorías de CallbackData; nada de strings a mano."""

from aiogram.filters.callback_data import CallbackData


class FightCB(CallbackData, prefix="f"):
    action: str  # "atk" | "potion" | "flee"
    fight_id: int
    turn: int
    user_id: int
