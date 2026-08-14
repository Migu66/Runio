"""Generación de enemigos. El azar entra siempre como parámetro."""

import random

from bot.game import balance
from bot.models import Monster

CREATURES: tuple[tuple[str, str], ...] = (
    ("Rata gigante", "🐀"),
    ("Goblin", "👺"),
    ("Esqueleto", "💀"),
    ("Lobo huargo", "🐺"),
    ("Bandido", "🗡"),
    ("Araña", "🕷"),
    ("Gólem", "🗿"),
    ("Espectro", "👻"),
    ("Ogro", "👹"),
    ("Basilisco", "🦎"),
    ("Quimera", "🦁"),
    ("Dragón joven", "🐉"),
)

# Epítetos invariables en género: valen igual para la rata y para el ogro.
EPITHETS_LOW = ("endeble", "torpe", "cobarde", "débil", "frágil", "ruin", "vulgar", "servil")
EPITHETS_MID = (
    "salvaje",
    "feroz",
    "audaz",
    "tenaz",
    "montaraz",
    "insolente",
    "hiriente",
    "voraz",
)
EPITHETS_HIGH = (
    "atroz",
    "cruel",
    "letal",
    "brutal",
    "infernal",
    "abisal",
    "ancestral",
    "espectral",
)

BOSS_PREFIXES = ("Gran", "Colosal", "Ancestral", "Descomunal", "Infernal", "Temible", "Implacable")
BOSS_EMOJI = "👑"


def epithets(level: int) -> tuple[str, ...]:
    low, high = balance.EPITHET_BANDS
    if level < low:
        return EPITHETS_LOW
    if level < high:
        return EPITHETS_MID
    return EPITHETS_HIGH


def is_boss_level(player_level: int) -> bool:
    return player_level % balance.BOSS_EVERY_LEVELS == 0


def generate(player_level: int, rng: random.Random) -> Monster:
    """Un enemigo del nivel del jugador, con su pizca de variación y opción a jefe."""
    level = max(1, player_level + rng.choice(balance.MONSTER_LEVEL_SPREAD))
    is_boss = is_boss_level(player_level) and rng.random() < balance.BOSS_CHANCE
    creature, emoji = rng.choice(CREATURES)

    hp = balance.MONSTER_HP_BASE + balance.MONSTER_HP_PER_LEVEL * level
    atk = round(balance.MONSTER_ATK_BASE + balance.MONSTER_ATK_PER_LEVEL * level)
    defense = round(balance.MONSTER_DEF_BASE + balance.MONSTER_DEF_PER_LEVEL * level)

    if is_boss:
        name = f"{rng.choice(BOSS_PREFIXES)} {creature.lower()}"
        emoji = BOSS_EMOJI
        hp = round(hp * balance.BOSS_HP_MULTIPLIER)
        atk = round(atk * balance.BOSS_ATK_MULTIPLIER)
    else:
        name = f"{creature} {rng.choice(epithets(level))}"

    return Monster(
        name=name,
        emoji=emoji,
        level=level,
        max_hp=hp,
        atk=atk,
        defense=defense,
        is_boss=is_boss,
    )
