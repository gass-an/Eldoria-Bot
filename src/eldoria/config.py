"""Module de configuration pour le bot Eldoria, chargé de lire les variables d'environnement nécessaires au fonctionnement du bot.

Comme le token Discord, les IDs pour la sauvegarde, et les paramètres de sauvegarde automatique.
"""

import os
from typing import Final

from dotenv import load_dotenv

# Charge .env une seule fois
load_dotenv()

TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")

# Pour save (optionnel si feature saves non utilisée)
MY_ID: Final[int | None] = int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
SAVE_GUILD_ID: Final[int | None] = int(os.getenv("GUILD_FOR_SAVE")) if os.getenv("GUILD_FOR_SAVE") else None
SAVE_CHANNEL_ID: Final[int | None] = int(os.getenv("CHANNEL_FOR_SAVE")) if os.getenv("CHANNEL_FOR_SAVE") else None

# Sauvegarde automatique (optionnel)
# - auto_save_time: format "HH:MM" (ex: "03:00")
# - auto_save_tz: timezone IANA (ex: "Pacific/Noumea", "Europe/Paris", "UTC")
# Si non défini, la sauvegarde auto est désactivée.
AUTO_SAVE_TIME: Final[str | None] = os.getenv("AUTO_SAVE_TIME")
AUTO_SAVE_TZ: Final[str] = os.getenv("AUTO_SAVE_TZ") or "UTC"
