"""Operaciones sobre la tabla players."""

import aiosqlite

from bot.db import transaction
from bot.game import balance, formulas
from bot.models import Player


def _to_player(row: aiosqlite.Row) -> Player:
    return Player(**dict(row))


async def get(db: aiosqlite.Connection, user_id: int) -> Player | None:
    async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    return _to_player(row) if row is not None else None


async def get_or_create(
    db: aiosqlite.Connection, user_id: int, name: str, now: int
) -> tuple[Player, bool]:
    """Devuelve (jugador, recién_creado) y mantiene el nombre al día con el de Telegram."""
    async with transaction(db):
        cur = await db.execute(
            """
            INSERT INTO players (user_id, name, level, xp, hp, gold, potions,
                                 energy, energy_ts, hp_ts, wins, losses, last_daily, created_at)
            VALUES (?, ?, 1, 0, ?, 0, ?, ?, ?, ?, 0, 0, 0, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (
                user_id,
                name,
                formulas.max_hp(1),
                balance.STARTING_POTIONS,
                balance.ENERGY_MAX,
                now,
                now,
                now,
            ),
        )
        created = cur.rowcount == 1
        if not created:
            await db.execute(
                "UPDATE players SET name = ? WHERE user_id = ? AND name <> ?",
                (name, user_id, name),
            )
        async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cur2:
            row = await cur2.fetchone()
    if row is None:  # pragma: no cover - imposible salvo corrupción
        raise RuntimeError(f"el jugador {user_id} no existe tras insertarlo")
    return _to_player(row), created
