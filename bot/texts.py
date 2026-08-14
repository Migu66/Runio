"""Todos los strings visibles para el usuario."""

import html

from bot.game import balance, formulas, loot
from bot.game.combat import Event
from bot.models import (
    SLOT_AMULET,
    SLOT_ARMOR,
    SLOT_WEAPON,
    Fight,
    Item,
    ItemDraft,
    Monster,
    Player,
    Stats,
)

BAR_WIDTH = 10
BAR_FULL = "█"
BAR_EMPTY = "░"

BTN_PROFILE = "👤 Perfil"
BTN_DUNGEON = "⚔️ Mazmorra"
BTN_INVENTORY = "🎒 Equipo"
BTN_SHOP = "🏪 Tienda"
BTN_RANKING = "🏆 Ranking"
BTN_DAILY = "🎁 Diario"
BTN_BUY_POTION = "🧪 Comprar poción ({price})"
BTN_SELL_LIST = "📦 Vender objetos"
BTN_SHOP_BACK = "◀ Volver a la tienda"
BTN_ATTACK = "⚔️ Atacar"
BTN_POTION = "🧪 Poción ({n})"
BTN_FLEE = "🏃 Huir"
BTN_PREV = "◀"
BTN_NEXT = "▶"

SLOT_NAMES = {"weapon": "Arma", "armor": "Armadura", "amulet": "Amuleto"}
SLOT_EMOJI = {"weapon": "🗡️", "armor": "🥋", "amulet": "📿"}
RARITY_NAMES = {
    "common": "Común",
    "uncommon": "Poco común",
    "rare": "Raro",
    "epic": "Épico",
    "legendary": "Legendario",
}

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

ENERGY_HINT = "   (+1 en {time})"

BOSS_TAG = "   👑 <b>JEFE</b>"

FIGHT = (
    "{emoji} <b>{monster}</b> — nivel {level}{boss}\n"
    "\n"
    "❤️ {player_bar} {player_hp}/{player_max}\n"
    "{emoji} {monster_bar} {monster_hp}/{monster_max}"
    "{log}"
)

EVENTS = {
    "player_hit": "⚔️ Le atizas para {amount} de daño",
    "player_hit_crit": "💥 ¡Crítico! Le abres en canal para {amount}",
    "monster_hit": "🩸 {monster} te alcanza para {amount}",
    "monster_hit_crit": "💥 ¡{monster} te revienta para {amount}!",
    "potion": "🧪 Apuras una poción y recuperas {amount}",
    "no_potions": "🧪 No te quedan pociones",
    "flee_ok": "🏃 Sales corriendo y esta vez cuela",
    "flee_fail": "🏃 Intentas huir y te cortan el paso",
    "win": "🏆 {monster} se desploma",
    "loss": "💀 Todo se vuelve negro",
    "draw": "🤝 Ninguno de los dos puede más",
}

VICTORY = (
    "🏆 <b>Victoria</b>\n\n"
    "Has acabado con {monster}.\n"
    "✨ +{xp} de experiencia   💰 +{gold} de oro"
    "{level_up}"
)
LEVEL_UP = "\n\n🎉 <b>¡Nivel {level}!</b> Te has recuperado del todo."
DEFEAT = (
    "💀 <b>Derrota</b>\n\n"
    "{monster} ha podido contigo.\n"
    "💰 Pierdes {gold} de oro.\n"
    "❤️ Despiertas con {hp}/{max_hp}. Ni la experiencia ni el equipo se tocan."
)
FLED = "🏃 <b>Huida</b>\n\nEscapas de {monster}. Sin premio, pero vivo."
DRAW = "🤝 <b>Tablas</b>\n\n{monster} y tú os quedáis sin fuelle. Nadie se lleva nada."

DROP = "\n\n🎁 Botín: {item}\n{comparison}"
DROP_BETTER = "▲ Mejora tu {slot} ({before} → {after})"
DROP_WORSE = "▼ Peor que tu {slot} ({before} → {after})"
DROP_EQUAL = "◆ Igual que tu {slot}"
DROP_EMPTY = "▲ Tienes la ranura de {slot} vacía"

INVENTORY = "🎒 <b>Mochila</b> — {total} objetos (página {page}/{pages})\n\n{items}\n\n{hint}"
INVENTORY_EMPTY = "🎒 Tu mochila está vacía. Baja a la /mazmorra a por algo."
INVENTORY_LINE = "{index}. {item}{equipped}"
INVENTORY_HINT = "Pulsa el número para equiparlo."
EQUIPPED_MARK = "  ✅"
EQUIPPED_OK = "Equipado: {item}"
ITEM_GONE = "Ese objeto ya no está en tu mochila"
NOT_YOURS = "Eso no es tuyo"

SHOP = (
    "🏪 <b>Tienda</b>\n\n"
    "💰 {gold} de oro   🧪 {potions} pociones\n\n"
    "Una poción cura el {heal}% de tu vida máxima y cuesta {price} de oro."
)
SHOP_SELL = (
    "📦 <b>Vender</b> — {total} objetos (página {page}/{pages})\n\n{items}\n\n"
    "Pulsa el número para venderlo. Lo que llevas puesto no aparece aquí."
)
SHOP_SELL_EMPTY = "📦 No tienes nada suelto que vender."
SELL_LINE = "{index}. {slot} {item} → 💰 {price}"
BOUGHT = "🧪 Poción comprada. Te quedan {gold} de oro."
NOT_ENOUGH_GOLD = "No te llega el oro: cuesta {price} y tienes {gold}"
SOLD = "Vendido por {price} de oro"
CANNOT_SELL_EQUIPPED = "Eso lo llevas puesto"

DAILY_OK = (
    "🎁 <b>Recompensa diaria</b>\n\n"
    "💰 +{gold} de oro   🧪 +{potions} pociones   ⚡ energía al máximo\n\n"
    "Vuelve dentro de {hours} horas."
)
DAILY_WAIT = "🎁 Ya la cobraste. Vuelve en {time}."

RANKING = "🏆 <b>Ranking</b>\n\n{rows}"
RANKING_ROW = "{medal} <b>{name}</b> — nivel {level} · {xp} XP"
RANKING_MEDALS = ("🥇", "🥈", "🥉")
RANKING_SELF = "\n\nTú vas el {rank}.º con nivel {level}."
RANKING_EMPTY = "🏆 Todavía no hay nadie en el ranking."

NO_ENERGY = "⚡ Te has quedado sin energía. Vuelve en {time}."
FIGHT_ALREADY_ACTIVE = "Ya tienes un combate en marcha. Resuélvelo antes de buscar otro."
NOT_YOUR_FIGHT = "Ese no es tu combate"
FIGHT_OVER = "Este combate ya terminó"
ALREADY_ACTED = "Ya has actuado"
NO_POTIONS_LEFT = "No te quedan pociones"


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


def number(value: int) -> str:
    """Separador de miles a la española: 4.869."""
    return f"{value:,}".replace(",", ".")


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


def item_stats(item: Item | ItemDraft) -> str:
    partes = []
    if item.atk:
        partes.append(f"⚔️{item.atk}")
    if item.defense:
        partes.append(f"🛡️{item.defense}")
    if item.crit:
        partes.append(f"🎯{item.crit}%")
    return " ".join(partes)


def format_item(item: Item | ItemDraft | None) -> str:
    if item is None:
        return EMPTY_SLOT
    return f"{loot.emoji(item.rarity)} {escape(item.name)} · {item_stats(item)}"


def render_drop(item: Item | ItemDraft, current: Item | None) -> str:
    """El ▲/▼ es lo que el jugador necesita para decidir en un segundo."""
    slot = SLOT_NAMES[item.slot].lower()
    if current is None:
        comparison = DROP_EMPTY.format(slot=slot)
    elif item.power > current.power:
        comparison = DROP_BETTER.format(slot=slot, before=current.power, after=item.power)
    elif item.power < current.power:
        comparison = DROP_WORSE.format(slot=slot, before=current.power, after=item.power)
    else:
        comparison = DROP_EQUAL.format(slot=slot)
    return DROP.format(item=format_item(item), comparison=comparison)


def render_inventory(
    items: list[Item], page: int, pages: int, total: int, equipped_ids: set[int]
) -> str:
    lines = [
        INVENTORY_LINE.format(
            index=index,
            slot=SLOT_EMOJI[item.slot],
            item=format_item(item),
            equipped=EQUIPPED_MARK if item.id in equipped_ids else "",
        )
        for index, item in enumerate(items, start=1)
    ]
    return INVENTORY.format(
        total=total, page=page, pages=pages, items="\n".join(lines), hint=INVENTORY_HINT
    )


def render_event(event: Event, monster: Monster) -> str:
    key = event.kind
    if event.is_crit and f"{key}_crit" in EVENTS:
        key = f"{key}_crit"
    return EVENTS[key].format(amount=event.amount, monster=escape(monster.name))


def render_fight(fight: Fight, player_max_hp: int) -> str:
    monster = fight.monster
    log = "\n\n" + "\n".join(fight.log) if fight.log else ""
    return FIGHT.format(
        emoji=monster.emoji,
        monster=escape(monster.name),
        level=monster.level,
        boss=BOSS_TAG if monster.is_boss else "",
        player_bar=progress_bar(fight.player_hp, player_max_hp),
        player_hp=fight.player_hp,
        player_max=player_max_hp,
        monster_bar=progress_bar(fight.monster_hp, monster.max_hp),
        monster_hp=fight.monster_hp,
        monster_max=monster.max_hp,
        log=log,
    )


def render_victory(monster: Monster, xp: int, gold: int, levels: int, level: int) -> str:
    return VICTORY.format(
        monster=escape(monster.name),
        xp=xp,
        gold=gold,
        level_up=LEVEL_UP.format(level=level) if levels else "",
    )


def render_defeat(monster: Monster, gold_lost: int, hp: int, max_hp_value: int) -> str:
    return DEFEAT.format(monster=escape(monster.name), gold=gold_lost, hp=hp, max_hp=max_hp_value)


def render_shop(player: Player) -> str:
    return SHOP.format(
        gold=number(player.gold),
        potions=player.potions,
        heal=round(balance.POTION_HEAL_PERCENT * 100),
        price=balance.POTION_PRICE,
    )


def render_sell_list(items: list[Item], page: int, pages: int, total: int) -> str:
    lines = [
        SELL_LINE.format(
            index=index,
            slot=SLOT_EMOJI[item.slot],
            item=format_item(item),
            price=number(loot.sell_price(item.item_level, item.rarity)),
        )
        for index, item in enumerate(items, start=1)
    ]
    return SHOP_SELL.format(total=total, page=page, pages=pages, items="\n".join(lines))


def render_ranking(leaders: list[Player], player: Player, rank: int) -> str:
    if not leaders:
        return RANKING_EMPTY
    rows = [
        RANKING_ROW.format(
            medal=RANKING_MEDALS[index] if index < len(RANKING_MEDALS) else f"{index + 1}.",
            name=escape(leader.name),
            level=leader.level,
            xp=number(leader.xp),
        )
        for index, leader in enumerate(leaders)
    ]
    text = RANKING.format(rows="\n".join(rows))
    if rank > len(leaders):
        text += RANKING_SELF.format(rank=rank, level=player.level)
    return text


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
        xp=number(player.xp),
        xp_next=number(xp_next),
        energy=player.energy,
        energy_max=balance.ENERGY_MAX,
        energy_hint=energy_hint,
        atk=stats.atk,
        defense=stats.defense,
        crit=stats.crit,
        weapon=format_item(equipped.get(SLOT_WEAPON)),
        armor=format_item(equipped.get(SLOT_ARMOR)),
        amulet=format_item(equipped.get(SLOT_AMULET)),
        gold=number(player.gold),
        potions=player.potions,
        wins=player.wins,
        losses=player.losses,
    )
