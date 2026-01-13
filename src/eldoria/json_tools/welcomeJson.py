import json
import random
from typing import Any, Dict

from ..db import gestionDB

def load_welcome_json() -> Dict[str, Any]:
    """Charge le fichier json/welcome_message.json.

    Le format du fichier peut évoluer : cette fonction renvoie simplement le JSON brut.
    """
    try:
        with open("./json/welcome_message.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def getWelcomeMessage(
    guild_id: int,
    *,
    user: str,
    server: str,
    recent_limit: int = 10,
) -> str:
    """Retourne un message de bienvenue choisi aléatoirement.

    - Tire un message depuis `json/welcome_message.json` (clé -> texte)
    - Évite (si possible) de retomber sur l'un des `recent_limit` derniers tirages
      dans la même guild (stocké en DB)
    - Enregistre le tirage en DB

    Placeholders supportés dans le JSON:
    - {user}
    - {server}
    """

    data = load_welcome_json() or {}
    messages = data.get("messages", {}) if isinstance(data, dict) else {}

    if not isinstance(messages, dict) or not messages:
        # fallback safe
        return f"👋 Bienvenue {user} !"

    # Nettoie/normalise
    pool: dict[str, str] = {
        str(k): v for k, v in messages.items() if isinstance(k, str) and isinstance(v, str) and v.strip()
    }
    if not pool:
        return f"👋 Bienvenue {user} !"

    recent_limit = max(0, int(recent_limit))
    recent_keys = (
        gestionDB.wm_get_recent_message_keys(guild_id, limit=recent_limit)
        if recent_limit > 0
        else []
    )

    available_keys = [k for k in pool.keys() if k not in set(recent_keys)]
    if not available_keys:
        # Si tous sont dans la fenêtre récente (petit pool), on autorise la répétition
        available_keys = list(pool.keys())

    chosen_key = random.choice(available_keys)
    raw = pool.get(chosen_key, "")

    # Remplacements
    msg = raw.replace("{user}", str(user)).replace("{server}", str(server))

    # Update historique
    gestionDB.wm_record_welcome_message(guild_id, chosen_key, keep=recent_limit)

    return msg