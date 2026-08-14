"""Middlewares del bot."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from bot import texts
from bot.repo import fights, players

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
