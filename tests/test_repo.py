"""Tests del acceso a datos sobre una base de datos temporal."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import TypeVar

import aiosqlite
import pytest

from bot import db as database
from bot.models import Monster
from bot.repo import fights, players

T = TypeVar("T")

MONSTER = Monster(
    name="Goblin salvaje", emoji="👺", level=5, max_hp=100, atk=16, defense=5, is_boss=False
)


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


def test_la_regeneracion_se_persiste_solo_cuando_cambia(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        player, _ = await players.get_or_create(db, 7, "Ana", 1_000)
        herido = replace(player, hp=10, energy=5, hp_ts=1_000, energy_ts=1_000)
        await db.execute(
            "UPDATE players SET hp = ?, energy = ?, hp_ts = ?, energy_ts = ? WHERE user_id = 7",
            (herido.hp, herido.energy, herido.hp_ts, herido.energy_ts),
        )

        quieto = await players.apply_regen(db, herido, 1_030)
        assert quieto is herido  # ni un ciclo completo: no se escribe

        fresco = await players.apply_regen(db, herido, 1_000 + 3 * 360)
        assert fresco.energy == 8
        assert fresco.hp > 10
        assert await players.get(db, 7) == fresco

    run_with_db(tmp_path, scenario)


def test_solo_puede_haber_un_combate_por_jugador(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)
        with pytest.raises(aiosqlite.IntegrityError):
            await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=3, now=1_001)

    run_with_db(tmp_path, scenario)


def test_el_combate_va_y_vuelve_de_la_base_de_datos(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        creado = await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)
        leido = await fights.get(db, 7)
        assert leido == creado
        assert leido is not None and leido.monster == MONSTER
        assert await fights.exists(db, 7) is True

    run_with_db(tmp_path, scenario)


def test_el_doble_toque_no_avanza_dos_veces_el_turno(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        fight = await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)

        assert await fights.advance(db, fight, 40, 30, ("primer golpe",)) is True
        assert await fights.advance(db, fight, 10, 5, ("golpe repetido",)) is False

        actual = await fights.get(db, 7)
        assert actual is not None
        assert (actual.turn, actual.player_hp, actual.monster_hp) == (1, 40, 30)
        assert actual.log == ("primer golpe",)

    run_with_db(tmp_path, scenario)


def test_solo_el_primero_cierra_el_combate(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        fight = await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)
        assert await fights.claim(db, fight) is True
        assert await fights.claim(db, fight) is False
        assert await fights.get(db, 7) is None

    run_with_db(tmp_path, scenario)


def test_el_registro_de_combate_se_queda_en_cuatro_lineas(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        fight = await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)
        await fights.advance(db, fight, 40, 30, tuple(f"línea {n}" for n in range(10)))
        actual = await fights.get(db, 7)
        assert actual is not None
        assert actual.log == ("línea 6", "línea 7", "línea 8", "línea 9")

    run_with_db(tmp_path, scenario)


def test_borrar_un_jugador_borra_su_combate(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        await fights.create(db, 7, MONSTER, 52, chat_id=1, message_id=2, now=1_000)
        await db.execute("DELETE FROM players WHERE user_id = 7")
        assert await fights.get(db, 7) is None

    run_with_db(tmp_path, scenario)


def test_las_migraciones_se_pueden_reaplicar(tmp_path: Path) -> None:
    async def scenario(db: aiosqlite.Connection) -> None:
        await players.get_or_create(db, 7, "Ana", 1_000)
        await database.run_migrations(db)
        assert await players.get(db, 7) is not None

    run_with_db(tmp_path, scenario)
