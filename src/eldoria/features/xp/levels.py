"""Module de logique métier pour la fonctionnalité de calcul de niveau à partir de l'XP."""

from collections.abc import Iterable


def compute_level(xp: int, levels: Iterable[tuple[int, int]]) -> int:
    """Renvoie le niveau correspondant à l'XP (plus haut seuil atteint)."""
    lvl = 1
    for level, required in levels:
        if xp >= required:
            lvl = level
    return lvl