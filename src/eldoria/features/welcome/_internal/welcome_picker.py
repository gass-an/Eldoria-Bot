"""Module de logique métier pour la fonctionnalité de messages de bienvenue.

Notamment le choix d'un message à partir du JSON de configuration et de l'historique récent.
"""

from __future__ import annotations

import random
from typing import Any


def pick_welcome_message(
    *,
    data: dict[str, Any],
    user: str,
    server: str,
    recent_keys: list[str],
    recent_limit: int = 10,
) -> tuple[str, str, list[str], str]:
    """Logique de choix d'un message de bienvenue à partir du JSON de configuration et de l'historique récent."""
    packs = data.get("packs", [])
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

            emojis: list[str] = []
            if isinstance(emojis_raw, list):
                emojis = [e for e in emojis_raw if isinstance(e, str) and e.strip()]

            for k, v in msgs.items():
                if isinstance(k, str) and isinstance(v, str) and v.strip():
                    pool[str(k)] = (title.strip(), v, emojis)

    if not pool:
        # fallback safe + chosen_key fixe
        msg = f"👋 Bienvenue {user} !"
        return ("👋 Bienvenue", msg, ["👋"], "fallback")

    recent_limit = max(0, int(recent_limit))
    recent_set = set(recent_keys[:recent_limit]) if isinstance(recent_keys, list) else set()

    available_keys = [k for k in pool.keys() if k not in recent_set]
    if not available_keys:
        available_keys = list(pool.keys())

    chosen_key = random.choice(available_keys)
    title, raw, emojis = pool.get(
        chosen_key,
        ("👋 Bienvenue", f"👋 Bienvenue {user} !", ["👋"]),
    )

    # Placeholders
    msg = raw.replace("{user}", str(user)).replace("{server}", str(server))

    # Max 2 emojis
    emojis = random.sample(emojis, k=min(len(emojis), 2)) if emojis else ["👋"]

    return (title, msg, emojis, chosen_key)
