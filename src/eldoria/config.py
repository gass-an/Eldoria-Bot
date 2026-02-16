"""Module de configuration pour le bot Eldoria, chargé de lire les variables d'environnement nécessaires au fonctionnement du bot.

Comme le token Discord, les IDs pour la sauvegarde, et les paramètres de sauvegarde automatique.
"""

import os
from typing import Final

from dotenv import load_dotenv


def env_str_required(name: str) -> str:
    """Récupère une variable d'environnement obligatoire et lève une exception si elle n'est pas définie."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_int_optional(name: str) -> int | None:
    """Récupère une variable d'environnement optionnelle, tente de la convertir en int, et retourne None si elle n'est pas définie ou si la conversion échoue."""
    value = os.getenv(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError as e:
        raise RuntimeError(f"Environment variable {name} must be an integer.") from e


def env_str_optional(name: str) -> str | None:
    """Récupère une variable d'environnement optionnelle et retourne None si elle n'est pas définie ou est vide."""
    value = os.getenv(name)
    return value if value else None


load_dotenv()

# === Discord (required) ===
TOKEN: Final[str] = env_str_required("DISCORD_TOKEN")

# === Backup system (all-or-nothing) ===
MY_ID: Final[int | None] = env_int_optional("ADMIN_USER_ID")
SAVE_GUILD_ID: Final[int | None] = env_int_optional("GUILD_FOR_SAVE")
SAVE_CHANNEL_ID: Final[int | None] = env_int_optional("CHANNEL_FOR_SAVE")

SAVE_ENABLED: Final[bool] = (MY_ID is not None or SAVE_GUILD_ID is not None or SAVE_CHANNEL_ID is not None)

if SAVE_ENABLED:
    missing = [name for name, v in [
        ("ADMIN_USER_ID", MY_ID),
        ("GUILD_FOR_SAVE", SAVE_GUILD_ID),
        ("CHANNEL_FOR_SAVE", SAVE_CHANNEL_ID),
    ] if v is None]
    if missing:
        raise RuntimeError(f"La fonctionnalité de sauvegarde est activée mais les variables suivantes sont manquantes : {', '.join(missing)}")
    
    assert MY_ID is not None
    assert SAVE_GUILD_ID is not None
    assert SAVE_CHANNEL_ID is not None

    SAVE_ADMIN_ID: Final[int] = MY_ID
    SAVE_GUILD: Final[int] = SAVE_GUILD_ID
    SAVE_CHANNEL: Final[int] = SAVE_CHANNEL_ID

# === Automatic backup (optional) ===
AUTO_SAVE_TIME: Final[str | None] = env_str_optional("AUTO_SAVE_TIME")
AUTO_SAVE_TZ: Final[str] = os.getenv("AUTO_SAVE_TZ") or "UTC"

AUTO_SAVE_ENABLED: Final[bool] = AUTO_SAVE_TIME is not None and AUTO_SAVE_TIME.strip() != ""
