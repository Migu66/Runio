"""Conexión única, migraciones y helper de transacciones."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def connect(db_path: Path) -> aiosqlite.Connection:
    """Abre la conexión del bot en autocommit para poder mandar BEGIN a mano."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path, isolation_level=None)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")
    return db


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Aplica en orden todos los .sql de migrations/; son idempotentes."""
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        logger.info("Aplicando migración %s", path.name)
        await db.executescript(path.read_text(encoding="utf-8"))


@asynccontextmanager
async def transaction(db: aiosqlite.Connection) -> AsyncIterator[aiosqlite.Connection]:
    """Toda lectura-modificación-escritura del mismo dato va aquí dentro."""
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
