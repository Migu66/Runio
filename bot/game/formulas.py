"""Progresión, regeneración y estadísticas efectivas. Funciones puras, sin azar ni estado."""

import math
from collections.abc import Iterable

from bot.game import balance
from bot.models import Item, Player, Stats


def xp_to_next(level: int) -> int:
    return int(balance.XP_BASE * level**balance.XP_EXPONENT)


def max_hp(level: int) -> int:
    return balance.HP_BASE + balance.HP_PER_LEVEL * level


def base_atk(level: int) -> int:
    return balance.ATK_BASE + balance.ATK_PER_LEVEL * level


def base_def(level: int) -> int:
    return balance.DEF_BASE + balance.DEF_PER_LEVEL * level


def apply_xp(level: int, xp: int, gained: int) -> tuple[int, int, int]:
    """Suma XP y sube todos los niveles que dé de sí; devuelve (nivel, xp, subidas)."""
    xp += gained
    levels = 0
    while xp >= xp_to_next(level):
        xp -= xp_to_next(level)
        level += 1
        levels += 1
    return level, xp, levels


def regen_energy(energy: int, energy_ts: int, now: int) -> tuple[int, int]:
    """Devuelve (energía_actual, nuevo_ts).

    Si ya está al máximo, el ts se adelanta a `now` para que no se acumule crédito
    invisible. Si no, solo se consumen los ciclos completos y el resto se arrastra.
    """
    energy = max(0, energy)
    if energy >= balance.ENERGY_MAX:
        return balance.ENERGY_MAX, now
    gained = max(0, (now - energy_ts) // balance.ENERGY_REGEN_SECONDS)
    if gained == 0:
        return energy, energy_ts
    return (
        min(balance.ENERGY_MAX, energy + gained),
        energy_ts + gained * balance.ENERGY_REGEN_SECONDS,
    )


def seconds_to_next_energy(energy: int, energy_ts: int, now: int) -> int:
    """Segundos hasta el siguiente punto. Espera valores ya regenerados; 0 si está llena."""
    if energy >= balance.ENERGY_MAX:
        return 0
    elapsed = max(0, now - energy_ts)
    return balance.ENERGY_REGEN_SECONDS - elapsed % balance.ENERGY_REGEN_SECONDS


def hp_per_cycle(max_hp_value: int) -> int:
    return math.ceil(max_hp_value * balance.HP_REGEN_PERCENT)


def regen_hp(hp: int, hp_ts: int, max_hp_value: int, now: int) -> tuple[int, int]:
    """Igual que la energía pero curando un porcentaje de la vida máxima por ciclo."""
    hp = max(0, hp)
    if hp >= max_hp_value:
        return max_hp_value, now
    cycles = max(0, (now - hp_ts) // balance.HP_REGEN_SECONDS)
    if cycles == 0:
        return hp, hp_ts
    healed = cycles * hp_per_cycle(max_hp_value)
    return (
        min(max_hp_value, hp + healed),
        hp_ts + cycles * balance.HP_REGEN_SECONDS,
    )


def effective_stats(player: Player, equipped: Iterable[Item]) -> Stats:
    """Base por nivel más lo que aporten los objetos equipados. El único sitio donde se suma."""
    atk = base_atk(player.level)
    defense = base_def(player.level)
    crit = balance.CRIT_BASE_CHANCE
    for item in equipped:
        atk += item.atk
        defense += item.defense
        crit += item.crit
    return Stats(atk=atk, defense=defense, crit=crit)
