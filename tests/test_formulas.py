"""Progresión y regeneración perezosa."""

import itertools

import pytest

from bot.game import balance, formulas
from bot.models import Item, Player

DAY = 86_400


def _player(level: int = 1, **kwargs: object) -> Player:
    base = dict(
        user_id=1,
        name="Ana",
        level=level,
        xp=0,
        hp=formulas.max_hp(level),
        gold=0,
        potions=3,
        energy=balance.ENERGY_MAX,
        energy_ts=0,
        hp_ts=0,
        weapon_id=None,
        armor_id=None,
        amulet_id=None,
        wins=0,
        losses=0,
        last_daily=0,
        created_at=0,
    )
    base.update(kwargs)
    return Player(**base)  # type: ignore[arg-type]


def _item(slot: str, atk: int = 0, defense: int = 0, crit: int = 0) -> Item:
    return Item(
        id=1,
        owner_id=1,
        slot=slot,
        name="Cosa",
        rarity="common",
        item_level=1,
        atk=atk,
        defense=defense,
        crit=crit,
        created_at=0,
    )


# --- progresión ---------------------------------------------------------------


def test_xp_to_next_es_estrictamente_creciente() -> None:
    valores = [formulas.xp_to_next(n) for n in range(1, 101)]
    assert all(b > a for a, b in itertools.pairwise(valores))


def test_la_tabla_de_referencia_se_cumple() -> None:
    niveles = (1, 5, 10, 20)
    assert [formulas.max_hp(n) for n in niveles] == [52, 100, 160, 280]
    assert [formulas.base_atk(n) for n in niveles] == [8, 16, 26, 46]
    assert [formulas.base_def(n) for n in niveles] == [3, 7, 12, 22]
    # La columna de XP del CLAUDE.md (40/465/1588/4869) no la produce ningún exponente:
    # manda la fórmula int(40 * nivel ** 1.6) que el propio documento escribe en código.
    assert [formulas.xp_to_next(n) for n in niveles] == [40, 525, 1592, 4827]


def test_se_pueden_subir_varios_niveles_de_golpe() -> None:
    nivel, xp, subidas = formulas.apply_xp(1, 0, 300)
    assert (nivel, subidas) == (3, 2)
    assert xp == 300 - formulas.xp_to_next(1) - formulas.xp_to_next(2)
    assert xp < formulas.xp_to_next(nivel)


def test_el_excedente_de_xp_se_arrastra() -> None:
    assert formulas.apply_xp(1, 39, 1) == (2, 0, 1)
    assert formulas.apply_xp(1, 0, 39) == (1, 39, 0)


# --- energía ------------------------------------------------------------------


@pytest.mark.parametrize("salto", [0, 359, 360, DAY])
@pytest.mark.parametrize("energia", [0, 1, 19, 20])
def test_la_energia_nunca_se_sale_del_rango(energia: int, salto: int) -> None:
    resultado, ts = formulas.regen_energy(energia, 0, salto)
    assert 0 <= resultado <= balance.ENERGY_MAX
    assert resultado >= energia
    assert ts <= salto or energia >= balance.ENERGY_MAX


def test_solo_cuentan_los_ciclos_completos() -> None:
    assert formulas.regen_energy(0, 0, 359) == (0, 0)
    assert formulas.regen_energy(0, 0, 360) == (1, 360)
    assert formulas.regen_energy(0, 0, 719) == (1, 360)


def test_el_resto_se_arrastra_entre_llamadas() -> None:
    energia, ts = formulas.regen_energy(0, 0, 359)
    assert energia == 0
    energia, ts = formulas.regen_energy(energia, ts, 359 * 2)
    assert energia == 1


def test_al_estar_llena_el_ts_se_adelanta() -> None:
    assert formulas.regen_energy(balance.ENERGY_MAX, 0, 5_000) == (balance.ENERGY_MAX, 5_000)


def test_un_dia_entero_no_pasa_del_maximo() -> None:
    assert formulas.regen_energy(0, 0, DAY) == (balance.ENERGY_MAX, DAY // 360 * 360)


def test_un_reloj_desajustado_no_resta_energia() -> None:
    assert formulas.regen_energy(5, 10_000, 9_000) == (5, 10_000)
    assert formulas.regen_energy(-3, 0, 0) == (0, 0)


def test_cuenta_atras_del_siguiente_punto() -> None:
    assert formulas.seconds_to_next_energy(balance.ENERGY_MAX, 0, 999) == 0
    assert formulas.seconds_to_next_energy(5, 0, 0) == 360
    assert formulas.seconds_to_next_energy(5, 0, 100) == 260
    assert formulas.seconds_to_next_energy(5, 0, 359) == 1


# --- vida ---------------------------------------------------------------------


@pytest.mark.parametrize("salto", [0, 119, 120, DAY])
def test_la_vida_nunca_supera_el_maximo(salto: int) -> None:
    tope = formulas.max_hp(5)
    for inicial in (0, 1, tope - 1, tope):
        vida, _ = formulas.regen_hp(inicial, 0, tope, salto)
        assert 0 <= vida <= tope
        assert vida >= inicial


def test_la_vida_regenera_por_ciclos_completos() -> None:
    tope = formulas.max_hp(5)  # 100 → 2 de vida por ciclo
    assert formulas.hp_per_cycle(tope) == 2
    assert formulas.regen_hp(50, 0, tope, 119) == (50, 0)
    assert formulas.regen_hp(50, 0, tope, 120) == (52, 120)
    assert formulas.regen_hp(50, 0, tope, 359) == (54, 240)


def test_la_vida_regenera_al_menos_un_punto_por_ciclo() -> None:
    assert formulas.hp_per_cycle(formulas.max_hp(1)) >= 1


# --- estadísticas efectivas ---------------------------------------------------


def test_las_estadisticas_efectivas_suman_el_equipo() -> None:
    player = _player(level=5)
    sin_equipo = formulas.effective_stats(player, [])
    assert (sin_equipo.atk, sin_equipo.defense, sin_equipo.crit) == (16, 7, 5)

    con_equipo = formulas.effective_stats(
        player,
        [
            _item("weapon", atk=10, crit=3),
            _item("armor", defense=6),
            _item("amulet", atk=2, defense=2, crit=1),
        ],
    )
    assert (con_equipo.atk, con_equipo.defense, con_equipo.crit) == (28, 15, 9)
