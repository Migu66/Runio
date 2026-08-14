"""Registro de todos los routers del bot."""

from aiogram import Dispatcher

from bot.handlers import daily, dungeon, inventory, profile, ranking, shop, start


def register_all(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(dungeon.router)
    dp.include_router(inventory.router)
    dp.include_router(shop.router)
    dp.include_router(ranking.router)
    dp.include_router(daily.router)
