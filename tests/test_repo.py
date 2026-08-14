"""Tests del acceso a datos sobre una base de datos temporal."""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import aiosqlite

from bot import db as database
from bot.repo import players

T = TypeVar("T")


def run_with_db(tmp_path: Path, scenario: Callable[[aiosqlite.Connection], Awaitable[T]]) -> T:
    """Abre una base de datos recién migrada, ejecuta el escenario y la cierra."""

    async def main() -> T:
        db = await database.connect(tmp_path / "test.db")
        try:
            await database.run_migrations(db)
            return await scenario(db)
        finally:
            await db.close()

    return asyncio.run(main())


def test_crear_personaje_es_idempotente(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        player, created = await players.get_or_create(db, 7, "Ana", 1_000)
        assert created is True
        assert player.level == 1
        assert player.hp == 52
        assert player.energy == 20
        assert player.potions == 3
        assert player.created_at == 1_000

        again, created_again = await players.get_or_create(db, 7, "Ana", 2_000)
        assert created_again is False
        assert again == player

    run_with_db(tmp_path, scenario)


def test_el_personaje_persiste_y_el_nombre_se_sincroniza(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        renamed, _ = await players.get_or_create(db, 7, "Ana la Roja", 1_500)
        assert renamed.name == "Ana la Roja"

        stored = await players.get(db, 7)
        assert stored == renamed
        assert await players.get(db, 8) is None

    run_with_db(tmp_path, scenario)


def test_las_migraciones_se_pueden_reaplicar(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        await database.run_migrations(db)
        assert await players.get(db, 7) is not None

    run_with_db(tmp_path, scenario)
