"""Registro de todos los routers del bot."""

from aiogram import Dispatcher

from bot.handlers import start


def register_all(dp: Dispatcher) -> None:
    dp.include_router(start.router)
