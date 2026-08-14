"""Progresión y estadísticas efectivas. Funciones puras, sin azar ni estado."""

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
