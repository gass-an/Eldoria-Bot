
from eldoria.features.xp.levels import compute_level


def test_compute_level_exact_thresholds():
    levels = [(1, 0), (2, 100), (3, 250)]

    assert compute_level(0, levels) == 1
    assert compute_level(100, levels) == 2
    assert compute_level(250, levels) == 3


def test_compute_level_between_thresholds():
    levels = [(1, 0), (2, 100), (3, 250)]

    assert compute_level(99, levels) == 1
    assert compute_level(101, levels) == 2
    assert compute_level(249, levels) == 2


def test_compute_level_above_highest_threshold():
    levels = [(1, 0), (2, 100), (3, 250)]
    assert compute_level(10_000, levels) == 3


def test_compute_level_empty_levels_returns_1():
    assert compute_level(123, []) == 1


def test_compute_level_negative_xp():
    levels = [(1, 0), (2, 100)]
    assert compute_level(-1, levels) == 1  # lvl initial = 1


def test_compute_level_unsorted_levels_behaviour_is_order_dependent():
    """
    IMPORTANT: avec l'impl actuelle, l'itération dépend de l'ordre.
    Si 'levels' n'est pas trié par required croissant, le résultat peut être surprenant.
    Ce test fige le comportement actuel.
    """
    # Ici, on place (3, 250) avant (2, 100)
    levels_unsorted = [(1, 0), (3, 250), (2, 100)]

    # xp=300 valide 3 puis 2 => lvl finit à 2 (car dernier match gagne)
    assert compute_level(300, levels_unsorted) == 2
