"""Middlewares del bot y captura global de errores."""

import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any

import aiosqlite
from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import CallbackQuery, ErrorEvent, Message, TelegramObject, User

from bot import texts
from bot.game import balance
from bot.repo import fights, players

logger = logging.getLogger(__name__)

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


def _is_start(event: TelegramObject) -> bool:
    if not isinstance(event, Message) or not event.text:
        return False
    return event.text.split(maxsplit=1)[0].split("@")[0] == "/start"


async def _ask_for_start(event: TelegramObject) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer(texts.NO_PLAYER, show_alert=True)
    elif isinstance(event, Message):
        await event.answer(texts.NO_PLAYER)


class ThrottlingMiddleware(BaseMiddleware):
    """Una acción por usuario cada THROTTLE_SECONDS. Lo que sobra se ignora sin contestar."""

    def __init__(self, seconds: float = balance.THROTTLE_SECONDS, capacity: int = 10_000) -> None:
        self._seconds = seconds
        self._capacity = capacity
        self._last: OrderedDict[int, float] = OrderedDict()

    def _too_soon(self, user_id: int, now: float) -> bool:
        previous = self._last.get(user_id)
        if previous is not None and now - previous < self._seconds:
            return True
        self._last[user_id] = now
        self._last.move_to_end(user_id)
        while len(self._last) > self._capacity:
            self._last.popitem(last=False)
        return False

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        if self._too_soon(user.id, time.monotonic()):
            if isinstance(event, CallbackQuery):
                await event.answer()  # el botón deja de girar aunque no hagamos nada
            return None
        return await handler(event, data)


class EnsurePlayerMiddleware(BaseMiddleware):
    """Inyecta data["player"] ya regenerado. Si no hay personaje y no es /start, corta."""

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)

        db: aiosqlite.Connection = data["db"]
        player = await players.get(db, user.id)
        if player is None:
            if _is_start(event):
                return await handler(event, data)
            await _ask_for_start(event)
            return None

        now = int(time.time())
        data["now"] = now
        # La vida no se regenera mientras hay un combate abierto.
        in_fight = await fights.exists(db, user.id)
        data["player"] = await players.apply_regen(db, player, now, heal=not in_fight)
        return await handler(event, data)


async def _on_error(event: ErrorEvent) -> bool:
    """Traza completa al log, disculpa genérica al jugador."""
    logger.exception(
        "Error procesando la actualización %s", event.update.update_id, exc_info=event.exception
    )
    update = event.update
    try:
        if update.callback_query is not None:
            await update.callback_query.answer(texts.SOMETHING_BROKE, show_alert=True)
        elif update.message is not None:
            await update.message.answer(texts.SOMETHING_BROKE)
    except Exception:
        # Si ni siquiera podemos disculparnos, queda en el log y seguimos.
        logger.exception("Tampoco se pudo avisar al jugador")
    return True


def setup(dp: Dispatcher) -> None:
    """Engancha middlewares y manejador de errores al dispatcher."""
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(ThrottlingMiddleware())
        observer.middleware(EnsurePlayerMiddleware())
    dp.errors.register(_on_error)
