import os
from typing import Final, Optional
from dotenv import load_dotenv

# Charge .env une seule fois
load_dotenv()

TOKEN: Final[Optional[str]] = os.getenv("discord_token")

# Pour save (optionnel si feature saves non utilisée)
MY_ID: Final[Optional[int]] = int(os.getenv("my_id")) if os.getenv("my_id") else None
SAVE_GUILD_ID: Final[Optional[int]] = int(os.getenv("guild_for_save")) if os.getenv("guild_for_save") else None
SAVE_CHANNEL_ID: Final[Optional[int]] = int(os.getenv("channel_for_save")) if os.getenv("channel_for_save") else None
