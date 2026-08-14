"""Todos los strings visibles para el usuario."""

import html

from bot.game import balance, formulas
from bot.models import SLOT_AMULET, SLOT_ARMOR, SLOT_WEAPON, Item, Player, Stats

BAR_WIDTH = 10
BAR_FULL = "█"
BAR_EMPTY = "░"

BTN_PROFILE = "👤 Perfil"

WELCOME = (
    "⚔️ <b>Runio</b>\n\n"
    "Bienvenido, <b>{name}</b>. Tu personaje ya está en pie: nivel 1, una vida entera "
    "por delante y ninguna cicatriz todavía.\n\n"
    "Mira tu ficha con /perfil."
)

WELCOME_BACK = "Ya tienes personaje, <b>{name}</b>. Mira tu ficha con /perfil."

NO_PLAYER = "Todavía no tienes personaje. Usa /start para crear uno."

PROFILE = (
    "👤 <b>{name}</b> — nivel {level}\n"
    "❤️ {hp_bar} {hp}/{max_hp}\n"
    "✨ {xp_bar} {xp}/{xp_next}\n"
    "⚡ {energy}/{energy_max}{energy_hint}\n"
    "\n"
    "⚔️ Ataque {atk}   🛡️ Defensa {defense}   🎯 Crítico {crit}%\n"
    "\n"
    "🗡️ Arma: {weapon}\n"
    "🥋 Armadura: {armor}\n"
    "📿 Amuleto: {amulet}\n"
    "\n"
    "💰 {gold} de oro   🧪 {potions} pociones\n"
    "🏆 {wins} victorias / {losses} derrotas"
)

EMPTY_SLOT = "—"


def escape(name: str) -> str:
    """Un jugador que se llame <b> no debe romper el parseo."""
    return html.escape(name)


def progress_bar(current: int, total: int, width: int = BAR_WIDTH) -> str:
    """Barra de bloques; si queda algo, se ve al menos un bloque."""
    if total <= 0:
        return BAR_FULL * width
    filled = round(width * current / total)
    filled = max(0, min(width, filled))
    if filled == 0 and current > 0:
        filled = 1
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def format_duration(seconds: int) -> str:
    """Segundos a algo legible: 45s, 4m 12s, 2h 5m."""
    seconds = max(0, seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


def format_item(item: Item | None) -> str:
    if item is None:
        return EMPTY_SLOT
    return escape(item.name)


def render_profile(
    player: Player,
    stats: Stats,
    equipped: dict[str, Item | None],
    energy_hint: str = "",
) -> str:
    max_hp = formulas.max_hp(player.level)
    xp_next = formulas.xp_to_next(player.level)
    return PROFILE.format(
        name=escape(player.name),
        level=player.level,
        hp_bar=progress_bar(player.hp, max_hp),
        hp=player.hp,
        max_hp=max_hp,
        xp_bar=progress_bar(player.xp, xp_next),
        xp=player.xp,
        xp_next=xp_next,
        energy=player.energy,
        energy_max=balance.ENERGY_MAX,
        energy_hint=energy_hint,
        atk=stats.atk,
        defense=stats.defense,
        crit=stats.crit,
        weapon=format_item(equipped.get(SLOT_WEAPON)),
        armor=format_item(equipped.get(SLOT_ARMOR)),
        amulet=format_item(equipped.get(SLOT_AMULET)),
        gold=player.gold,
        potions=player.potions,
        wins=player.wins,
        losses=player.losses,
    )
