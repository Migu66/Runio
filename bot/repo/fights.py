"""Operaciones sobre la tabla fights.

Las escrituras que cierran o avanzan un turno son comparaciones-e-intercambio sobre
la columna `turn`: si otro toque se ha adelantado, devuelven False en vez de repetir
el daño. Las que no abren transacción esperan que el handler las envuelva.
"""

import json
from dataclasses import asdict

import aiosqlite

from bot.game import balance
from bot.models import Fight, Monster


def _dump_monster(monster: Monster) -> str:
    return json.dumps(asdict(monster), ensure_ascii=False)


def _load_monster(raw: str) -> Monster:
    return Monster(**json.loads(raw))


def _to_fight(row: aiosqlite.Row) -> Fight:
    data = dict(row)
    data["monster"] = _load_monster(data["monster"])
    data["log"] = tuple(json.loads(data["log"]))
    return Fight(**data)


async def get(db: aiosqlite.Connection, user_id: int) -> Fight | None:
    async with db.execute("SELECT * FROM fights WHERE user_id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
    return _to_fight(row) if row is not None else None


async def exists(db: aiosqlite.Connection, user_id: int) -> bool:
    async with db.execute("SELECT 1 FROM fights WHERE user_id = ?", (user_id,)) as cur:
        return await cur.fetchone() is not None


async def create(
    db: aiosqlite.Connection,
    user_id: int,
    monster: Monster,
    player_hp: int,
    chat_id: int,
    message_id: int,
    now: int,
) -> Fight:
    """El UNIQUE de user_id garantiza que no haya dos combates a la vez."""
    cur = await db.execute(
        """
        INSERT INTO fights (user_id, monster, player_hp, monster_hp, turn,
                            chat_id, message_id, log, created_at)
        VALUES (?, ?, ?, ?, 0, ?, ?, '[]', ?)
        """,
        (user_id, _dump_monster(monster), player_hp, monster.max_hp, chat_id, message_id, now),
    )
    return Fight(
        id=int(cur.lastrowid or 0),
        user_id=user_id,
        monster=monster,
        player_hp=player_hp,
        monster_hp=monster.max_hp,
        turn=0,
        chat_id=chat_id,
        message_id=message_id,
        log=(),
        created_at=now,
    )


async def advance(
    db: aiosqlite.Connection,
    fight: Fight,
    player_hp: int,
    monster_hp: int,
    log: tuple[str, ...],
) -> bool:
    """Escribe el turno siguiente solo si en la base de datos sigue el turno esperado."""
    cur = await db.execute(
        """
        UPDATE fights SET player_hp = ?, monster_hp = ?, turn = ?, log = ?
        WHERE id = ? AND turn = ?
        """,
        (
            player_hp,
            monster_hp,
            fight.turn + 1,
            json.dumps(list(log[-balance.LOG_LINES :]), ensure_ascii=False),
            fight.id,
            fight.turn,
        ),
    )
    return cur.rowcount == 1


async def claim(db: aiosqlite.Connection, fight: Fight) -> bool:
    """Cierra el combate. False si otro toque ya lo había cerrado."""
    cur = await db.execute("DELETE FROM fights WHERE id = ? AND turn = ?", (fight.id, fight.turn))
    return cur.rowcount == 1


async def set_message(
    db: aiosqlite.Connection, fight_id: int, chat_id: int, message_id: int
) -> None:
    await db.execute(
        "UPDATE fights SET chat_id = ?, message_id = ? WHERE id = ?",
        (chat_id, message_id, fight_id),
    )
