"""Valeurs par défaut centralisées.

Objectif : ne pas dupliquer les mêmes valeurs (config/paliers) dans plusieurs fichiers.
Le reste du code doit importer depuis ici.
"""

from __future__ import annotations

from typing import Final


# -------------------- XP system --------------------

# Doit rester cohérent avec les DEFAULT du schéma SQL (xp_config).
XP_CONFIG_DEFAULTS: Final[dict[str, int | bool]] = {
    "enabled": False,
    "points_per_message": 8,
    "cooldown_seconds": 90,
    "bonus_percent": 20,
    "karuta_k_small_percent": 30,
}


# Paliers XP (niveaux 1 → 5)
XP_LEVELS_DEFAULTS: Final[dict[int, int]] = {
    1: 0,
    2: 600,
    3: 1800,
    4: 3800,
    5: 7200,
}
