"""Registro de todos los routers del bot."""

from aiogram import Dispatcher

from bot.handlers import dungeon, inventory, profile, start


def register_all(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(dungeon.router)
    dp.include_router(inventory.router)
