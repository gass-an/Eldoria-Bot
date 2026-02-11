"""Module de configuration d'XP pour un serveur, avec des valeurs par défaut provenant de XP_CONFIG_DEFAULTS."""

from dataclasses import dataclass

from eldoria.defaults import XP_CONFIG_DEFAULTS


@dataclass(frozen=True)
class XpConfig:
    """Configuration d'XP pour un serveur, avec des valeurs par défaut provenant de XP_CONFIG_DEFAULTS."""

    enabled: bool = bool(XP_CONFIG_DEFAULTS["enabled"])
    points_per_message: int = int(XP_CONFIG_DEFAULTS["points_per_message"])
    cooldown_seconds: int = int(XP_CONFIG_DEFAULTS["cooldown_seconds"])
    bonus_percent: int = int(XP_CONFIG_DEFAULTS["bonus_percent"])
    # Pour les petits messages (<=10) qui commencent par "k" (commandes Karuta)
    # on n'attribue qu'un certain pourcentage de l'XP.
    # Ex: 30 => 30% de l'XP normal.
    karuta_k_small_percent: int = int(XP_CONFIG_DEFAULTS["karuta_k_small_percent"])

    # ---- Vocal XP ----
    voice_enabled: bool = bool(XP_CONFIG_DEFAULTS.get("voice_enabled", True))
    voice_xp_per_interval: int = int(XP_CONFIG_DEFAULTS.get("voice_xp_per_interval", 1))
    voice_interval_seconds: int = int(XP_CONFIG_DEFAULTS.get("voice_interval_seconds", 180))
    voice_daily_cap_xp: int = int(XP_CONFIG_DEFAULTS.get("voice_daily_cap_xp", 100))

    # 0 = auto (system_channel / #general si trouvable), sinon ID du salon.
    voice_levelup_channel_id: int = int(XP_CONFIG_DEFAULTS.get("voice_levelup_channel_id", 0))