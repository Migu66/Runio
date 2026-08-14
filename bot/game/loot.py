"""Generación de objetos. El azar entra siempre como parámetro."""

import random

from bot.game import balance
from bot.models import SLOT_AMULET, SLOT_ARMOR, SLOT_WEAPON, SLOTS, ItemDraft

NOUNS: dict[str, tuple[str, ...]] = {
    SLOT_WEAPON: ("Espada", "Hacha", "Maza", "Daga", "Lanza", "Martillo", "Cimitarra", "Guadaña"),
    SLOT_ARMOR: ("Cota", "Coraza", "Armadura", "Loriga", "Peto", "Brigantina"),
    SLOT_AMULET: ("Amuleto", "Colgante", "Talismán", "Medallón", "Reliquia", "Sello"),
}

# Complementos con preposición: valen igual para la espada que para el martillo.
SUFFIXES: dict[str, tuple[str, ...]] = {
    "common": ("de hierro", "de cuero", "de bronce", "de madera"),
    "uncommon": ("de acero", "de plata", "de roble", "de guerra"),
    "rare": ("de obsidiana", "de escarcha", "del trueno", "de los páramos"),
    "epic": ("del abismo", "del ocaso", "de sangre", "de la tormenta"),
    "legendary": ("del dragón", "de las estrellas", "del vacío", "del primer rey"),
}


def rarity_rank(rarity: str) -> int:
    return next(i for i, row in enumerate(balance.RARITIES) if row[0] == rarity)


def multiplier(rarity: str) -> float:
    return balance.RARITIES[rarity_rank(rarity)][2]


def emoji(rarity: str) -> str:
    return balance.RARITIES[rarity_rank(rarity)][3]


def roll_rarity(rng: random.Random) -> str:
    tirada = rng.random()
    acumulado = 0.0
    for name, probability, _, _ in balance.RARITIES:
        acumulado += probability
        if tirada < acumulado:
            return name
    return balance.RARITIES[-1][0]


def item_power(item_level: int, rarity: str, rng: random.Random) -> int:
    """Potencia bruta a repartir entre las estadísticas de la ranura."""
    base = balance.ITEM_POWER_BASE + balance.ITEM_POWER_PER_LEVEL * item_level
    value = base * multiplier(rarity) * rng.uniform(*balance.ITEM_POWER_VARIANCE)
    return max(1, round(value))


def item_name(slot: str, rarity: str, rng: random.Random) -> str:
    return f"{rng.choice(NOUNS[slot])} {rng.choice(SUFFIXES[rarity])}"


def generate(item_level: int, rng: random.Random) -> ItemDraft:
    """Un objeto del nivel del monstruo que lo ha soltado."""
    slot = rng.choice(SLOTS)
    rarity = roll_rarity(rng)
    power = item_power(item_level, rarity, rng)
    atk = defense = crit = 0

    if slot == SLOT_WEAPON:
        atk = power
        if rarity_rank(rarity) >= balance.WEAPON_CRIT_MIN_RANK:
            crit = rng.randint(*balance.WEAPON_CRIT_RANGE)
    elif slot == SLOT_ARMOR:
        defense = power
    else:
        atk = max(1, round(power * balance.AMULET_ATK_SHARE))
        defense = max(1, power - atk)
        crit = rng.randint(*balance.AMULET_CRIT_RANGE)

    return ItemDraft(
        slot=slot,
        name=item_name(slot, rarity, rng),
        rarity=rarity,
        item_level=item_level,
        atk=atk,
        defense=defense,
        crit=crit,
    )


def roll(item_level: int, rng: random.Random) -> ItemDraft | None:
    """Tirada de botín tras una victoria. None si el monstruo no suelta nada."""
    if rng.random() >= balance.LOOT_CHANCE:
        return None
    return generate(item_level, rng)
