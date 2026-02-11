"""Module de logique métier pour la fonctionnalité de messages de bienvenue."""

from eldoria.db.repo import welcome_message_repo
from eldoria.features.welcome._internal.welcome_picker import pick_welcome_message
from eldoria.json_tools.welcome_json import load_welcome_json


def get_welcome_message(
        guild_id: int,
        *,
        user: str,
        server: str,
        recent_limit: int = 10,
    ) -> tuple[str, str, list[str]]:
        """Retourne un message de bienvenue à envoyer pour un nouvel arrivant, en fonction de la configuration JSON et de l'historique récent."""
        # 1) Charger le JSON
        data = load_welcome_json()

        # 2) Lire l'historique récent (DB)
        recent_keys = (
            welcome_message_repo.wm_get_recent_message_keys(guild_id, limit=recent_limit)
            if recent_limit > 0
            else []
        )

        # 3) Choisir le message (logique pure)
        title, msg, emojis, chosen_key = pick_welcome_message(
            data=data,
            user=user,
            server=server,
            recent_keys=recent_keys,
            recent_limit=recent_limit,
        )

        # 4) Persister le tirage
        if chosen_key and chosen_key != "fallback":
            welcome_message_repo.wm_record_welcome_message(
                guild_id,
                chosen_key,
                keep=recent_limit,
            )

        return title, msg, emojis