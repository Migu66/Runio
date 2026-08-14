"""Dataclasses que viajan entre la base de datos, la lógica del juego y los handlers."""

from dataclasses import dataclass

SLOT_WEAPON = "weapon"
SLOT_ARMOR = "armor"
SLOT_AMULET = "amulet"
SLOTS: tuple[str, ...] = (SLOT_WEAPON, SLOT_ARMOR, SLOT_AMULET)


@dataclass(frozen=True, slots=True)
class Player:
    user_id: int
    name: str
    level: int
    xp: int
    hp: int
    gold: int
    potions: int
    energy: int
    energy_ts: int
    hp_ts: int
    weapon_id: int | None
    armor_id: int | None
    amulet_id: int | None
    wins: int
    losses: int
    last_daily: int
    created_at: int

    def equipped_id(self, slot: str) -> int | None:
        return {
            SLOT_WEAPON: self.weapon_id,
            SLOT_ARMOR: self.armor_id,
            SLOT_AMULET: self.amulet_id,
        }[slot]


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    owner_id: int
    slot: str
    name: str
    rarity: str
    item_level: int
    atk: int
    defense: int
    crit: int
    created_at: int

    @property
    def power(self) -> int:
        """Suma de estadísticas, la cifra con la que se comparan dos objetos."""
        return self.atk + self.defense + self.crit


@dataclass(frozen=True, slots=True)
class Monster:
    name: str
    emoji: str
    level: int
    max_hp: int
    atk: int
    defense: int
    is_boss: bool


@dataclass(frozen=True, slots=True)
class Fight:
    id: int
    user_id: int
    monster: Monster
    player_hp: int
    monster_hp: int
    turn: int
    chat_id: int
    message_id: int
    log: tuple[str, ...]
    created_at: int


@dataclass(frozen=True, slots=True)
class Stats:
    atk: int
    defense: int
    crit: int
