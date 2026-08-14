PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS players (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    level         INTEGER NOT NULL DEFAULT 1,
    xp            INTEGER NOT NULL DEFAULT 0,
    hp            INTEGER NOT NULL,
    gold          INTEGER NOT NULL DEFAULT 0,
    potions       INTEGER NOT NULL DEFAULT 3,
    energy        INTEGER NOT NULL,
    energy_ts     INTEGER NOT NULL,
    hp_ts         INTEGER NOT NULL,
    weapon_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    armor_id      INTEGER REFERENCES items(id) ON DELETE SET NULL,
    amulet_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    wins          INTEGER NOT NULL DEFAULT 0,
    losses        INTEGER NOT NULL DEFAULT 0,
    last_daily    INTEGER NOT NULL DEFAULT 0,
    created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    slot       TEXT    NOT NULL CHECK (slot IN ('weapon','armor','amulet')),
    name       TEXT    NOT NULL,
    rarity     TEXT    NOT NULL,
    item_level INTEGER NOT NULL,
    atk        INTEGER NOT NULL DEFAULT 0,
    def        INTEGER NOT NULL DEFAULT 0,
    crit       INTEGER NOT NULL DEFAULT 0,   -- puntos porcentuales
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id, slot);

CREATE TABLE IF NOT EXISTS fights (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES players(user_id) ON DELETE CASCADE,
    monster     TEXT    NOT NULL,           -- JSON del Monster
    player_hp   INTEGER NOT NULL,
    monster_hp  INTEGER NOT NULL,
    turn        INTEGER NOT NULL DEFAULT 0,
    chat_id     INTEGER NOT NULL,
    message_id  INTEGER NOT NULL,
    log         TEXT    NOT NULL DEFAULT '[]',  -- JSON, últimas 4 líneas
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ranking ON players(level DESC, xp DESC);
