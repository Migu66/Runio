"""Operaciones sobre la tabla players."""

from dataclasses import replace

import aiosqlite

from bot.db import transaction
from bot.game import balance, formulas
from bot.models import Player


def _to_player(row: aiosqlite.Row) -> Player:
    return Player(**dict(row))


def _regenerated(player: Player, now: int, heal: bool) -> Player:
    """El mismo objeto si no cambia nada, para poder ahorrarnos la escritura."""
    energy, energy_ts = formulas.regen_energy(player.energy, player.energy_ts, now)
    hp, hp_ts = player.hp, player.hp_ts
    if heal:
        hp, hp_ts = formulas.regen_hp(player.hp, player.hp_ts, formulas.max_hp(player.level), now)
    if energy == player.energy and hp == player.hp:
        return player
    return replace(player, energy=energy, energy_ts=energy_ts, hp=hp, hp_ts=hp_ts)


async def get(db: aiosqlite.Connection, user_id: int) -> Player | None:
    async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    return _to_player(row) if row is not None else None


async def apply_regen(
    db: aiosqlite.Connection, player: Player, now: int, *, heal: bool = True
) -> Player:
    """Regeneración perezosa de energía y vida; solo escribe si algún valor sube."""
    if _regenerated(player, now, heal) is player:
        return player
    async with transaction(db):
        current = await get(db, player.user_id)
        if current is None:  # pragma: no cover - el jugador se borró entre medias
            return player
        fresh = _regenerated(current, now, heal)
        await db.execute(
            "UPDATE players SET energy = ?, energy_ts = ?, hp = ?, hp_ts = ? WHERE user_id = ?",
            (fresh.energy, fresh.energy_ts, fresh.hp, fresh.hp_ts, fresh.user_id),
        )
    return fresh


async def set_energy(db: aiosqlite.Connection, user_id: int, energy: int, energy_ts: int) -> None:
    """Escritura suelta; el handler la envuelve en su transacción."""
    await db.execute(
        "UPDATE players SET energy = ?, energy_ts = ? WHERE user_id = ?",
        (energy, energy_ts, user_id),
    )


async def set_potions(db: aiosqlite.Connection, user_id: int, potions: int) -> None:
    await db.execute("UPDATE players SET potions = ? WHERE user_id = ?", (potions, user_id))


async def save_after_fight(db: aiosqlite.Connection, player: Player) -> None:
    """Vuelca todo lo que puede cambiar al terminar un combate."""
    await db.execute(
        """
        UPDATE players SET level = ?, xp = ?, hp = ?, hp_ts = ?, gold = ?,
                           potions = ?, wins = ?, losses = ?
        WHERE user_id = ?
        """,
        (
            player.level,
            player.xp,
            player.hp,
            player.hp_ts,
            player.gold,
            player.potions,
            player.wins,
            player.losses,
            player.user_id,
        ),
    )


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
