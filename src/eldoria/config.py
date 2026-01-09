import os
from typing import Final, Optional
from dotenv import load_dotenv

# Charge .env une seule fois
load_dotenv()

TOKEN: Final[Optional[str]] = os.getenv("DISCORD_TOKEN")

# Pour save (optionnel si feature saves non utilisée)
MY_ID: Final[Optional[int]] = int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
SAVE_GUILD_ID: Final[Optional[int]] = int(os.getenv("GUILD_FOR_SAVE")) if os.getenv("GUILD_FOR_SAVE") else None
SAVE_CHANNEL_ID: Final[Optional[int]] = int(os.getenv("CHANNEL_FOR_SAVE")) if os.getenv("CHANNEL_FOR_SAVE") else None

# Sauvegarde automatique (optionnel)
# - auto_save_time: format "HH:MM" (ex: "03:00")
# - auto_save_tz: timezone IANA (ex: "Pacific/Noumea", "Europe/Paris", "UTC")
# Si non défini, la sauvegarde auto est désactivée.
AUTO_SAVE_TIME: Final[Optional[str]] = os.getenv("AUTO_SAVE_TIME")
AUTO_SAVE_TZ: Final[str] = os.getenv("AUTO_SAVE_TZ") or "UTC"
