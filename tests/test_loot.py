"""Rarezas, potencia y reparto por ranura."""

import itertools
import random
from collections import Counter

import pytest

from bot.game import balance, loot
from bot.models import SLOT_AMULET, SLOT_ARMOR, SLOT_WEAPON, SLOTS

RARITIES = [row[0] for row in balance.RARITIES]


def test_la_distribucion_de_rarezas_se_parece_a_la_tabla() -> None:
    rng = random.Random(42)
    tiradas = Counter(loot.roll_rarity(rng) for _ in range(100_000))
    for name, esperada, _, _ in balance.RARITIES:
        observada = tiradas[name] / 100_000
        assert observada == pytest.approx(esperada, rel=0.10), (
            f"{name}: {observada:.4%} frente a {esperada:.1%}"
        )


def test_las_probabilidades_suman_uno() -> None:
    assert sum(row[1] for row in balance.RARITIES) == pytest.approx(1.0)


def test_las_estadisticas_siempre_llegan_a_uno() -> None:
    rng = random.Random(7)
    for _ in range(20_000):
        item = loot.generate(rng.randint(1, 30), rng)
        assert item.power >= 1
        assert item.atk >= 0 and item.defense >= 0 and item.crit >= 0
        if item.slot == SLOT_WEAPON:
            assert item.atk >= 1 and item.defense == 0
        elif item.slot == SLOT_ARMOR:
            assert item.defense >= 1 and item.atk == 0 and item.crit == 0
        else:
            assert item.atk >= 1 and item.defense >= 1 and item.crit >= 1


def test_solo_las_armas_raras_o_mejores_llevan_critico() -> None:
    rng = random.Random(3)
    for _ in range(20_000):
        item = loot.generate(rng.randint(1, 30), rng)
        if item.slot != SLOT_WEAPON:
            continue
        if loot.rarity_rank(item.rarity) < balance.WEAPON_CRIT_MIN_RANK:
            assert item.crit == 0
        else:
            assert balance.WEAPON_CRIT_RANGE[0] <= item.crit <= balance.WEAPON_CRIT_RANGE[1]


def test_la_curva_de_nivel_domina_a_la_rareza() -> None:
    """Un legendario de nivel 1 se queda corto frente a un común de nivel 20."""
    rng = random.Random(11)
    legendario = max(loot.item_power(1, "legendary", rng) for _ in range(5_000))
    comun = min(loot.item_power(20, "common", rng) for _ in range(5_000))
    assert legendario < comun


def test_la_rareza_sube_la_potencia_al_mismo_nivel() -> None:
    rng = random.Random(5)
    medias = [
        sum(loot.item_power(10, rarity, rng) for _ in range(2_000)) / 2_000 for rarity in RARITIES
    ]
    assert all(b > a for a, b in itertools.pairwise(medias))


def test_el_botin_cae_cerca_del_porcentaje_previsto() -> None:
    rng = random.Random(1)
    caidas = sum(loot.roll(5, rng) is not None for _ in range(50_000))
    assert caidas / 50_000 == pytest.approx(balance.LOOT_CHANCE, rel=0.05)


def test_todas_las_ranuras_salen_y_los_nombres_varian() -> None:
    rng = random.Random(2)
    generados = [loot.generate(5, rng) for _ in range(2_000)]
    assert {item.slot for item in generados} == set(SLOTS)
    assert len({item.name for item in generados}) > 40
    for item in generados:
        assert item.item_level == 5
        assert item.rarity in RARITIES


def test_el_nivel_del_objeto_es_el_del_monstruo() -> None:
    rng = random.Random(4)
    for nivel in (1, 7, 25):
        item = loot.generate(nivel, rng)
        assert item.item_level == nivel


def test_el_amuleto_reparte_la_potencia_a_medias() -> None:
    rng = random.Random(6)
    amuletos = [i for i in (loot.generate(20, rng) for _ in range(3_000)) if i.slot == SLOT_AMULET]
    assert amuletos
    for item in amuletos:
        assert abs(item.atk - item.defense) <= 1
