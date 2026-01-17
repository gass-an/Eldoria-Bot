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

    # ---- Vocal XP ----
    # Le système global XP doit être activé pour que ça fonctionne.
    # 1 XP / 3 minutes par défaut, cap journalier = 5h => 100 XP max / jour.
    # Le bonus "Server Tag" s'applique aussi au vocal, mais le cap reste identique
    # (le bonus permet juste d'atteindre le cap plus vite).
    "voice_enabled": True,
    "voice_xp_per_interval": 1,
    "voice_interval_seconds": 180,
    "voice_daily_cap_xp": 100,

    # Salon (texte) où annoncer les passages de niveaux dus au vocal.
    # 0 = auto (system_channel / #general si trouvable), sinon ID du salon.
    "voice_levelup_channel_id": 0,
}


# Paliers XP (niveaux 1 → 5)
XP_LEVELS_DEFAULTS: Final[dict[int, int]] = {
    1: 0,
    2: 600,
    3: 1800,
    4: 3800,
    5: 7200,
}
