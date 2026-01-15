import json
import random
from typing import Any, Dict, Tuple

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



import random
from typing import Tuple, List

def getWelcomeMessage(
    guild_id: int,
    *,
    user: str,
    server: str,
    recent_limit: int = 10,
) -> Tuple[str, str, List[str]]:
    """Retourne (title, message, emojis) de bienvenue choisi aléatoirement.

    - Tire un message depuis `json/welcome_message.json` au format:
      {
        "packs": [
          {"title": "...", "messages": {"w01": "...", ...}, "emojis": ["👋", ...]},
          ...
        ]
      }

    - Évite (si possible) de retomber sur l'un des `recent_limit` derniers tirages
      dans la même guild (stocké en DB via la clé: w01, w02, ...)
    - Enregistre le tirage en DB

    Placeholders supportés dans le JSON:
    - {user}
    - {server}
    """

    data = load_welcome_json() or {}
    packs = data.get("packs", []) if isinstance(data, dict) else []

    # pool: key -> (title, raw_message, emojis)
    pool: dict[str, tuple[str, str, list[str]]] = {}

    if isinstance(packs, list):
        for pack in packs:
            if not isinstance(pack, dict):
                continue

            title = pack.get("title", "")
            msgs = pack.get("messages", {})
            emojis_raw = pack.get("emojis", [])

            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(msgs, dict) or not msgs:
                continue

            # Nettoie/normalise la liste d'emojis (optionnelle)
            emojis: list[str] = []
            if isinstance(emojis_raw, list):
                emojis = [e for e in emojis_raw if isinstance(e, str) and e.strip()]

            for k, v in msgs.items():
                if isinstance(k, str) and isinstance(v, str) and v.strip():
                    pool[str(k)] = (title.strip(), v, emojis)

    if not pool:
        # fallback safe
        return ("👋 Bienvenue", f"👋 Bienvenue {user} !", ["👋"])

    recent_limit = max(0, int(recent_limit))
    recent_keys = (
        gestionDB.wm_get_recent_message_keys(guild_id, limit=recent_limit)
        if recent_limit > 0
        else []
    )

    recent_set = set(recent_keys) if isinstance(recent_keys, list) else set()

    available_keys = [k for k in pool.keys() if k not in recent_set]
    if not available_keys:
        # Si tous sont dans la fenêtre récente (petit pool), on autorise la répétition
        available_keys = list(pool.keys())

    chosen_key = random.choice(available_keys)
    title, raw, emojis = pool.get(
        chosen_key,
        ("👋 Bienvenue", f"👋 Bienvenue {user} !", ["👋"])
    )

    # Remplacements
    msg = raw.replace("{user}", str(user)).replace("{server}", str(server))

    # Récupère 2 emojis dans la liste
    emojis = random.sample(emojis, k=min(len(emojis), 2))

    # Update historique
    gestionDB.wm_record_welcome_message(guild_id, chosen_key, keep=recent_limit)

    return (title, msg, emojis)
