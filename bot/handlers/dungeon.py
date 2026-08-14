"""Inicio de combate y resolución de turnos."""

import logging
import random
from dataclasses import replace

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import keyboards, texts
from bot.callbacks import FightCB
from bot.db import transaction
from bot.game import balance, combat, formulas, monsters
from bot.models import Fight, Player
from bot.repo import fights, players

logger = logging.getLogger(__name__)
router = Router(name="dungeon")

_rng = random.Random()


async def _safe_edit(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    markup: InlineKeyboardMarkup | None,
) -> bool:
    """Edita el mensaje del combate. False si Telegram ya no lo encuentra."""
    try:
        await bot.edit_message_text(
            text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup
        )
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return True
        logger.info("No se pudo editar el mensaje %s: %s", message_id, exc)
        return False


async def _drop_keyboard(cb: CallbackQuery) -> None:
    """Quita los botones de un combate que ya no existe."""
    if not isinstance(cb.message, Message):
        return
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as exc:
        logger.info("No se pudo limpiar el teclado: %s", exc)


async def _show(message: Message, db: aiosqlite.Connection, fight: Fight, player: Player) -> None:
    """Manda el mensaje del combate y lo deja apuntado en la fila."""
    sent = await message.answer(
        texts.render_fight(fight, formulas.max_hp(player.level)),
        reply_markup=keyboards.fight(fight, player.potions),
    )
    async with transaction(db):
        await fights.set_message(db, fight.id, sent.chat.id, sent.message_id)


async def _reattach(
    message: Message, db: aiosqlite.Connection, fight: Fight, player: Player
) -> None:
    """Reengancha el combate abierto en su mensaje en vez de abrir otro."""
    edited = False
    if fight.message_id:
        edited = await _safe_edit(
            message.bot,
            fight.chat_id,
            fight.message_id,
            texts.render_fight(fight, formulas.max_hp(player.level)),
            keyboards.fight(fight, player.potions),
        )
    if edited:
        await message.answer(texts.FIGHT_ALREADY_ACTIVE)
    else:
        await _show(message, db, fight, player)


@router.message(Command("mazmorra"))
@router.message(F.text == texts.BTN_DUNGEON)
async def cmd_dungeon(message: Message, db: aiosqlite.Connection, player: Player, now: int) -> None:
    open_fight = await fights.get(db, player.user_id)
    if open_fight is not None:
        await _reattach(message, db, open_fight, player)
        return

    monster = monsters.generate(player.level, _rng)
    problem: str | None = None
    fight: Fight | None = None

    async with transaction(db):
        current = await players.get(db, player.user_id)
        if current is None:  # pragma: no cover - el jugador se borró entre medias
            problem = texts.NO_PLAYER
        elif await fights.exists(db, current.user_id):
            problem = texts.FIGHT_ALREADY_ACTIVE
        else:
            spent = formulas.spend_energy(
                current.energy, current.energy_ts, now, balance.ENERGY_COST_DUNGEON
            )
            if spent is None:
                energy, energy_ts = formulas.regen_energy(current.energy, current.energy_ts, now)
                wait = formulas.seconds_to_next_energy(energy, energy_ts, now)
                problem = texts.NO_ENERGY.format(time=texts.format_duration(wait))
            else:
                await players.set_energy(db, current.user_id, spent[0], spent[1])
                fight = await fights.create(
                    db, current.user_id, monster, current.hp, chat_id=0, message_id=0, now=now
                )

    if problem is not None:
        await message.answer(problem)
        return
    if fight is None:  # pragma: no cover - una de las dos ramas siempre asigna
        return
    await _show(message, db, fight, player)


def _apply_outcome(
    player: Player, monster_fight: Fight, state: combat.CombatState, now: int
) -> tuple[Player, str]:
    """Traduce el final del combate a un jugador actualizado y su mensaje de resumen."""
    monster = monster_fight.monster

    if state.outcome == combat.WIN:
        xp, gold = combat.victory_rewards(monster, _rng)
        level, left, levels = formulas.apply_xp(player.level, player.xp, xp)
        hp = formulas.max_hp(level) if levels else state.player_hp
        updated = replace(
            player,
            level=level,
            xp=left,
            hp=hp,
            hp_ts=now,
            gold=player.gold + gold,
            potions=state.potions,
            wins=player.wins + 1,
        )
        return updated, texts.render_victory(monster, xp, gold, levels, level)

    if state.outcome == combat.LOSS:
        max_hp = formulas.max_hp(player.level)
        lost = formulas.death_gold_loss(player.gold)
        hp = formulas.death_hp(max_hp)
        updated = replace(
            player,
            hp=hp,
            hp_ts=now,
            gold=player.gold - lost,
            potions=state.potions,
            losses=player.losses + 1,
        )
        return updated, texts.render_defeat(monster, lost, hp, max_hp)

    updated = replace(player, hp=state.player_hp, hp_ts=now, potions=state.potions)
    plantilla = texts.FLED if state.outcome == combat.FLED else texts.DRAW
    return updated, plantilla.format(monster=texts.escape(monster.name))


@router.callback_query(FightCB.filter())
async def on_fight_action(
    cb: CallbackQuery,
    callback_data: FightCB,
    db: aiosqlite.Connection,
    player: Player,
    now: int,
) -> None:
    if cb.from_user.id != callback_data.user_id:
        await cb.answer(texts.NOT_YOUR_FIGHT, show_alert=True)
        return

    fight = await fights.get(db, player.user_id)
    if fight is None or fight.id != callback_data.fight_id:
        await cb.answer(texts.FIGHT_OVER)
        await _drop_keyboard(cb)
        return

    if callback_data.turn != fight.turn:
        await cb.answer(texts.ALREADY_ACTED)
        return

    max_hp = formulas.max_hp(player.level)
    state = combat.CombatState(
        stats=formulas.effective_stats(player, []),
        player_hp=fight.player_hp,
        player_max_hp=max_hp,
        potions=player.potions,
        monster=fight.monster,
        monster_hp=fight.monster_hp,
        turn=fight.turn,
    )
    new_state, events = combat.resolve_turn(state, callback_data.action, _rng)

    if any(event.kind == combat.EV_NO_POTIONS for event in events):
        await cb.answer(texts.NO_POTIONS_LEFT, show_alert=True)
        return

    log = (fight.log + tuple(texts.render_event(e, fight.monster) for e in events))[
        -balance.LOG_LINES :
    ]

    if new_state.finished:
        updated_player, summary = _apply_outcome(player, fight, new_state, now)
        async with transaction(db):
            claimed = await fights.claim(db, fight)
            if claimed:
                await players.save_after_fight(db, updated_player)
        if not claimed:
            await cb.answer(texts.ALREADY_ACTED)
            return
        closed = replace(
            fight,
            player_hp=new_state.player_hp,
            monster_hp=new_state.monster_hp,
            turn=new_state.turn,
            log=log,
        )
        await _edit_fight(cb, closed, max_hp, markup=None)
        if isinstance(cb.message, Message):
            await cb.message.answer(summary)
        await cb.answer()
        return

    async with transaction(db):
        advanced = await fights.advance(db, fight, new_state.player_hp, new_state.monster_hp, log)
        if advanced and new_state.potions != player.potions:
            await players.set_potions(db, player.user_id, new_state.potions)
    if not advanced:
        await cb.answer(texts.ALREADY_ACTED)
        return

    ongoing = replace(
        fight,
        player_hp=new_state.player_hp,
        monster_hp=new_state.monster_hp,
        turn=new_state.turn,
        log=log,
    )
    await _edit_fight(cb, ongoing, max_hp, keyboards.fight(ongoing, new_state.potions))
    await cb.answer()


async def _edit_fight(
    cb: CallbackQuery, fight: Fight, player_max_hp: int, markup: InlineKeyboardMarkup | None
) -> None:
    """Durante el combate se edita siempre el mismo mensaje, nunca se manda uno nuevo."""
    if not isinstance(cb.message, Message):
        return
    await _safe_edit(
        cb.bot,
        cb.message.chat.id,
        cb.message.message_id,
        texts.render_fight(fight, player_max_hp),
        markup,
    )
