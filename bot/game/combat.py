"""Motor de combate por turnos. Función pura: estado + acción + rng → estado + eventos."""

import random
from dataclasses import dataclass, replace

from bot.game import balance
from bot.models import Monster, Stats

ACTION_ATTACK = "atk"
ACTION_POTION = "potion"
ACTION_FLEE = "flee"
ACTIONS = (ACTION_ATTACK, ACTION_POTION, ACTION_FLEE)

ONGOING = "ongoing"
WIN = "win"
LOSS = "loss"
FLED = "fled"
DRAW = "draw"

EV_PLAYER_HIT = "player_hit"
EV_MONSTER_HIT = "monster_hit"
EV_POTION = "potion"
EV_NO_POTIONS = "no_potions"
EV_FLEE_OK = "flee_ok"
EV_FLEE_FAIL = "flee_fail"
EV_WIN = "win"
EV_LOSS = "loss"
EV_DRAW = "draw"


@dataclass(frozen=True, slots=True)
class Event:
    kind: str
    amount: int = 0
    is_crit: bool = False


@dataclass(frozen=True, slots=True)
class CombatState:
    stats: Stats
    player_hp: int
    player_max_hp: int
    potions: int
    monster: Monster
    monster_hp: int
    turn: int = 0
    outcome: str = ONGOING

    @property
    def finished(self) -> bool:
        return self.outcome != ONGOING


def compute_damage(
    atk: int, defense: int, crit_chance: int, rng: random.Random
) -> tuple[int, bool]:
    """Mitigación con rendimientos decrecientes: siempre se hace al menos 1 de daño."""
    raw = atk * rng.uniform(*balance.DAMAGE_VARIANCE)
    mitigated = raw * 100 / (100 + defense * balance.DEFENSE_K)
    is_crit = rng.randint(1, 100) <= crit_chance
    if is_crit:
        mitigated *= balance.CRIT_MULTIPLIER
    return max(1, round(mitigated)), is_crit


def potion_heal(max_hp: int) -> int:
    return round(max_hp * balance.POTION_HEAL_PERCENT)


def victory_rewards(monster: Monster, rng: random.Random) -> tuple[int, int]:
    """(xp, oro) por derrotar al monstruo; los jefes pagan más."""
    xp = int(balance.XP_REWARD_BASE * monster.level**balance.XP_REWARD_EXPONENT)
    gold = rng.randint(*balance.GOLD_REWARD_RANGE) * monster.level
    if monster.is_boss:
        xp = round(xp * balance.BOSS_REWARD_MULTIPLIER)
        gold = round(gold * balance.BOSS_REWARD_MULTIPLIER)
    return xp, gold


def resolve_turn(
    state: CombatState, action: str, rng: random.Random
) -> tuple[CombatState, list[Event]]:
    """Resuelve un turno. No muta el estado recibido, así repetirlo no duplica daño."""
    if state.finished:
        return state, []
    if action not in ACTIONS:
        raise ValueError(f"acción desconocida: {action!r}")

    events: list[Event] = []
    player_hp = state.player_hp
    monster_hp = state.monster_hp
    potions = state.potions
    outcome = ONGOING
    monster_answers = True

    if action == ACTION_ATTACK:
        damage, is_crit = compute_damage(
            state.stats.atk, state.monster.defense, state.stats.crit, rng
        )
        monster_hp = max(0, monster_hp - damage)
        events.append(Event(EV_PLAYER_HIT, damage, is_crit))
        if monster_hp == 0:
            outcome = WIN
            monster_answers = False

    elif action == ACTION_POTION:
        if potions <= 0:
            return state, [Event(EV_NO_POTIONS)]  # no gasta turno
        healed = min(state.player_max_hp, player_hp + potion_heal(state.player_max_hp)) - player_hp
        player_hp += healed
        potions -= 1
        events.append(Event(EV_POTION, healed))

    else:  # ACTION_FLEE
        if rng.random() < balance.FLEE_CHANCE:
            outcome = FLED
            monster_answers = False
            events.append(Event(EV_FLEE_OK))
        else:
            events.append(Event(EV_FLEE_FAIL))

    if monster_answers:
        damage, is_crit = compute_damage(
            state.monster.atk, state.stats.defense, balance.CRIT_BASE_CHANCE, rng
        )
        player_hp = max(0, player_hp - damage)
        events.append(Event(EV_MONSTER_HIT, damage, is_crit))
        if player_hp == 0:
            outcome = LOSS

    turn = state.turn + 1
    if outcome == ONGOING and turn >= balance.MAX_TURNS:
        outcome = DRAW

    if outcome == WIN:
        events.append(Event(EV_WIN))
    elif outcome == LOSS:
        events.append(Event(EV_LOSS))
    elif outcome == DRAW:
        events.append(Event(EV_DRAW))

    new_state = replace(
        state,
        player_hp=player_hp,
        monster_hp=monster_hp,
        potions=potions,
        turn=turn,
        outcome=outcome,
    )
    return new_state, events
