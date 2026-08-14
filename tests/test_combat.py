"""Motor de combate: daño, turnos, idempotencia y balanceo."""

import random
from dataclasses import replace

import pytest

from bot.game import balance, combat, formulas, monsters
from bot.models import Monster, Stats


class FixedRandom(random.Random):
    """rng con random() fijo, para forzar el resultado de una huida."""

    def __init__(self, value: float, seed: int = 0) -> None:
        super().__init__(seed)
        self._value = value

    def random(self) -> float:
        return self._value


def _state(level: int = 5, potions: int = 0, monster: Monster | None = None) -> combat.CombatState:
    monster = monster or monsters.generate(level, random.Random(0))
    return combat.CombatState(
        stats=Stats(
            atk=formulas.base_atk(level),
            defense=formulas.base_def(level),
            crit=balance.CRIT_BASE_CHANCE,
        ),
        player_hp=formulas.max_hp(level),
        player_max_hp=formulas.max_hp(level),
        potions=potions,
        monster=monster,
        monster_hp=monster.max_hp,
    )


def _play(state: combat.CombatState, rng: random.Random) -> combat.CombatState:
    """Ataca siempre, y bebe si le queda poco y tiene con qué."""
    while not state.finished:
        tocado = state.player_hp < state.player_max_hp * 0.35
        action = combat.ACTION_POTION if tocado and state.potions else combat.ACTION_ATTACK
        state, _ = combat.resolve_turn(state, action, rng)
    return state


# --- daño ---------------------------------------------------------------------


def test_el_dano_nunca_baja_de_uno() -> None:
    rng = random.Random(1)
    for _ in range(1_000):
        damage, _ = combat.compute_damage(1, 9_999, 0, rng)
        assert damage >= 1


def test_la_defensa_reduce_el_dano_pero_no_lo_anula() -> None:
    sin_defensa = [combat.compute_damage(50, 0, 0, random.Random(n))[0] for n in range(200)]
    con_defensa = [combat.compute_damage(50, 20, 0, random.Random(n))[0] for n in range(200)]
    assert sum(con_defensa) < sum(sin_defensa)
    assert min(con_defensa) >= 1


def test_el_critico_multiplica() -> None:
    normal, hubo_critico = combat.compute_damage(100, 0, 0, random.Random(3))
    critico, hubo_critico_2 = combat.compute_damage(100, 0, 100, random.Random(3))
    assert hubo_critico is False and hubo_critico_2 is True
    assert critico == pytest.approx(normal * balance.CRIT_MULTIPLIER, abs=1)


# --- turnos -------------------------------------------------------------------


def test_un_combate_completo_termina_antes_del_tope() -> None:
    final = _play(_state(), random.Random(42))
    assert final.outcome in (combat.WIN, combat.LOSS)
    assert final.turn < balance.MAX_TURNS


def test_el_tope_de_turnos_declara_tablas() -> None:
    muro = Monster(
        name="Muro", emoji="🧱", level=1, max_hp=99_999, atk=1, defense=9_999, is_boss=False
    )
    final = _play(_state(monster=muro), random.Random(7))
    assert final.outcome == combat.DRAW
    assert final.turn == balance.MAX_TURNS


def test_repetir_el_turno_no_aplica_el_dano_dos_veces() -> None:
    inicial = _state()
    primero, _ = combat.resolve_turn(inicial, combat.ACTION_ATTACK, random.Random(5))
    repetido, _ = combat.resolve_turn(inicial, combat.ACTION_ATTACK, random.Random(5))
    assert primero == repetido
    assert primero.turn == inicial.turn + 1
    assert inicial.monster_hp == inicial.monster.max_hp  # el estado de partida no se toca


def test_un_combate_terminado_ya_no_avanza() -> None:
    final = _play(_state(), random.Random(42))
    repetido, eventos = combat.resolve_turn(final, combat.ACTION_ATTACK, random.Random(0))
    assert repetido is final
    assert eventos == []


def test_una_accion_desconocida_revienta() -> None:
    with pytest.raises(ValueError):
        combat.resolve_turn(_state(), "bailar", random.Random(0))


# --- pociones -----------------------------------------------------------------


def test_la_pocion_no_pasa_del_maximo() -> None:
    rng = random.Random(11)
    base = _state(potions=3)
    for vida in (1, base.player_max_hp // 2, base.player_max_hp - 1, base.player_max_hp):
        curado, _ = combat.resolve_turn(replace(base, player_hp=vida), combat.ACTION_POTION, rng)
        assert curado.player_hp <= curado.player_max_hp
        assert curado.potions == base.potions - 1


def test_curarse_cuesta_el_turno() -> None:
    base = replace(_state(potions=1), player_hp=10)
    curado, eventos = combat.resolve_turn(base, combat.ACTION_POTION, random.Random(4))
    assert combat.EV_MONSTER_HIT in [e.kind for e in eventos]
    assert curado.turn == base.turn + 1


def test_sin_pociones_no_se_gasta_el_turno() -> None:
    state = _state(potions=0)
    resultado, eventos = combat.resolve_turn(state, combat.ACTION_POTION, random.Random(2))
    assert resultado is state
    assert [e.kind for e in eventos] == [combat.EV_NO_POTIONS]


# --- huida --------------------------------------------------------------------


def test_huir_bien_termina_el_combate_sin_recompensa() -> None:
    state = _state()
    fugado, eventos = combat.resolve_turn(state, combat.ACTION_FLEE, FixedRandom(0.0))
    assert fugado.outcome == combat.FLED
    assert [e.kind for e in eventos] == [combat.EV_FLEE_OK]
    assert fugado.player_hp == state.player_hp  # el monstruo no llega a pegar


def test_huir_mal_regala_un_golpe_al_monstruo() -> None:
    state = _state()
    fallido, eventos = combat.resolve_turn(state, combat.ACTION_FLEE, FixedRandom(0.99))
    assert fallido.outcome == combat.ONGOING
    assert [e.kind for e in eventos] == [combat.EV_FLEE_FAIL, combat.EV_MONSTER_HIT]
    assert fallido.player_hp < state.player_hp


# --- recompensas y balanceo ---------------------------------------------------


def test_los_jefes_pagan_dos_veces_y_media() -> None:
    normal = Monster("Bicho", "🐀", 5, 100, 16, 5, is_boss=False)
    jefe = Monster("Gran bicho", "👑", 5, 160, 21, 5, is_boss=True)
    xp_normal, oro_normal = combat.victory_rewards(normal, random.Random(4))
    xp_jefe, oro_jefe = combat.victory_rewards(jefe, random.Random(4))
    assert xp_jefe == round(xp_normal * balance.BOSS_REWARD_MULTIPLIER)
    assert oro_jefe == round(oro_normal * balance.BOSS_REWARD_MULTIPLIER)


def test_la_tasa_de_victoria_de_un_nivel_5_sin_equipo() -> None:
    """1.000 combates con el generador real: ni un paseo ni un muro."""
    rng = random.Random(42)
    victorias = 0
    for _ in range(1_000):
        state = _state(level=5, potions=balance.STARTING_POTIONS, monster=monsters.generate(5, rng))
        if _play(state, rng).outcome == combat.WIN:
            victorias += 1
    assert 550 <= victorias <= 800, f"tasa de victoria {victorias / 10:.1f}%"


# --- monstruos ----------------------------------------------------------------


def test_el_monstruo_sigue_al_jugador_de_cerca() -> None:
    rng = random.Random(9)
    for player_level in (1, 3, 7, 15):
        for _ in range(200):
            monster = monsters.generate(player_level, rng)
            assert 1 <= monster.level <= player_level + 1
            assert monster.max_hp > 0 and monster.atk > 0 and monster.defense > 0
            assert monster.name and monster.emoji


def test_los_jefes_solo_aparecen_cada_cinco_niveles() -> None:
    rng = random.Random(3)
    assert not any(monsters.generate(4, rng).is_boss for _ in range(500))
    jefes = sum(monsters.generate(5, rng).is_boss for _ in range(2_000))
    assert 0.25 < jefes / 2_000 < 0.45


def test_un_jefe_pega_y_aguanta_mas() -> None:
    rng = random.Random(0)
    jefes = [m for m in (monsters.generate(10, rng) for _ in range(2_000)) if m.is_boss]
    assert jefes
    for jefe in jefes:
        hp_base = balance.MONSTER_HP_BASE + balance.MONSTER_HP_PER_LEVEL * jefe.level
        atk_base = round(balance.MONSTER_ATK_BASE + balance.MONSTER_ATK_PER_LEVEL * jefe.level)
        assert jefe.max_hp == round(hp_base * balance.BOSS_HP_MULTIPLIER)
        assert jefe.atk == round(atk_base * balance.BOSS_ATK_MULTIPLIER)
        assert jefe.emoji == monsters.BOSS_EMOJI


def test_los_nombres_varian() -> None:
    rng = random.Random(1)
    nombres = {monsters.generate(3, rng).name for _ in range(200)}
    assert len(nombres) > 20
