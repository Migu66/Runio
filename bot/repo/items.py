"""Operaciones sobre la tabla items.

La columna se llama `def`, que en Python es palabra reservada: en el dataclass es
`defense` y aquí se traduce en cada consulta.
"""

import aiosqlite

from bot.models import SLOT_AMULET, SLOT_ARMOR, SLOT_WEAPON, SLOTS, Item, ItemDraft, Player

_COLUMNS = """id, owner_id, slot, name, rarity, item_level,
              atk, "def" AS defense, crit, created_at"""

_SLOT_COLUMN = {SLOT_WEAPON: "weapon_id", SLOT_ARMOR: "armor_id", SLOT_AMULET: "amulet_id"}


def _to_item(row: aiosqlite.Row) -> Item:
    return Item(**dict(row))


async def create(db: aiosqlite.Connection, owner_id: int, draft: ItemDraft, now: int) -> Item:
    cur = await db.execute(
        """
        INSERT INTO items (owner_id, slot, name, rarity, item_level, atk, "def", crit, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            draft.slot,
            draft.name,
            draft.rarity,
            draft.item_level,
            draft.atk,
            draft.defense,
            draft.crit,
            now,
        ),
    )
    return Item(
        id=int(cur.lastrowid or 0),
        owner_id=owner_id,
        slot=draft.slot,
        name=draft.name,
        rarity=draft.rarity,
        item_level=draft.item_level,
        atk=draft.atk,
        defense=draft.defense,
        crit=draft.crit,
        created_at=now,
    )


async def get(db: aiosqlite.Connection, item_id: int) -> Item | None:
    async with db.execute(f"SELECT {_COLUMNS} FROM items WHERE id = ?", (item_id,)) as cur:
        row = await cur.fetchone()
    return _to_item(row) if row is not None else None


async def count_owned(db: aiosqlite.Connection, owner_id: int) -> int:
    async with db.execute("SELECT COUNT(*) FROM items WHERE owner_id = ?", (owner_id,)) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row is not None else 0


async def page(db: aiosqlite.Connection, owner_id: int, limit: int, offset: int) -> list[Item]:
    """Los últimos conseguidos primero, que es lo que el jugador quiere ver."""
    async with db.execute(
        f"SELECT {_COLUMNS} FROM items WHERE owner_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
        (owner_id, limit, offset),
    ) as cur:
        rows = await cur.fetchall()
    return [_to_item(row) for row in rows]


async def position(db: aiosqlite.Connection, owner_id: int, item_id: int) -> int:
    """Índice del objeto en la lista paginada, empezando en 0."""
    async with db.execute(
        "SELECT COUNT(*) FROM items WHERE owner_id = ? AND id > ?", (owner_id, item_id)
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row is not None else 0


async def get_equipped(db: aiosqlite.Connection, player: Player) -> dict[str, Item | None]:
    equipped: dict[str, Item | None] = dict.fromkeys(SLOTS)
    ids = [i for i in (player.weapon_id, player.armor_id, player.amulet_id) if i is not None]
    if not ids:
        return equipped
    marks = ",".join("?" * len(ids))
    async with db.execute(f"SELECT {_COLUMNS} FROM items WHERE id IN ({marks})", ids) as cur:
        rows = await cur.fetchall()
    for row in rows:
        item = _to_item(row)
        equipped[item.slot] = item
    return equipped


async def equip(db: aiosqlite.Connection, user_id: int, item: Item) -> None:
    column = _SLOT_COLUMN[item.slot]  # de un diccionario fijo, nunca de la entrada del usuario
    await db.execute(
        f"UPDATE players SET {column} = ? WHERE user_id = ?",
        (item.id, user_id),
    )


async def delete(db: aiosqlite.Connection, item_id: int) -> None:
    await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
