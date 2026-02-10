from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from eldoria.db.repo import welcome_message_repo

@dataclass(slots=True)
class WelcomeService:
    """Service métier pour la gestion des messages de bienvenue et de l'historique anti-répétition."""

    # ------------ Config -----------

    def ensure_defaults(self, guild_id: int, *, enabled: bool = False, channel_id: int = 0) -> None:
        """Crée la configuration de bienvenue si elle n'existe pas (avec des valeurs par défaut)."""
        return welcome_message_repo.wm_ensure_defaults(guild_id, enabled=enabled, channel_id=channel_id)

    def get_config(self, guild_id: int) -> Dict[str, Any]:
        """Retourne la configuration de bienvenue (enabled + channel_id), en la créant si absente."""
        return welcome_message_repo.wm_get_config(guild_id)

    def set_config(
        self,
        guild_id: int,
        *,
        enabled: Optional[bool] = None,
        channel_id: Optional[int] = None,
    ) -> None:
        """Met à jour partiellement la configuration (enabled et/ou channel_id)."""
        return welcome_message_repo.wm_set_config(guild_id, enabled=enabled, channel_id=channel_id)

    def set_enabled(self, guild_id: int, enabled: bool) -> None:
        """Active/désactive les messages de bienvenue pour un serveur."""
        return welcome_message_repo.wm_set_enabled(guild_id, enabled)

    def set_channel_id(self, guild_id: int, channel_id: int) -> None:
        """Définit le salon cible où envoyer les messages de bienvenue."""
        return welcome_message_repo.wm_set_channel_id(guild_id, channel_id)

    def is_enabled(self, guild_id: int) -> bool:
        """Indique si les messages de bienvenue sont activés pour un serveur."""
        return welcome_message_repo.wm_is_enabled(guild_id)

    def get_channel_id(self, guild_id: int) -> int:
        """Retourne le salon configuré pour la bienvenue (0 si non configuré)."""
        return welcome_message_repo.wm_get_channel_id(guild_id)

    def delete_config(self, guild_id: int) -> None:
        """Réinitialise complètement la configuration de bienvenue d'un serveur."""
        return welcome_message_repo.wm_delete_config(guild_id)

    # ------------ Historique (anti-répétition) -----------

    def get_recent_message_keys(self, guild_id: int, *, limit: int = 10) -> List[str]:
        """Retourne les dernières clés de messages utilisées, du plus récent au plus ancien."""
        return welcome_message_repo.wm_get_recent_message_keys(guild_id, limit=limit)

    def record_welcome_message(
        self,
        guild_id: int,
        message_key: str,
        *,
        used_at: Optional[int] = None,
        keep: int = 10,
    ) -> None:
        """Enregistre une clé de message utilisée et ne conserve que les `keep` plus récentes."""
        return welcome_message_repo.wm_record_welcome_message(guild_id, message_key, used_at=used_at, keep=keep)