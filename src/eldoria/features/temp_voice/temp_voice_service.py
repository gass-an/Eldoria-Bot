"""Service métier pour la gestion des salons vocaux temporaires."""

from dataclasses import dataclass

from eldoria.db.repo import temp_voice_repo


@dataclass(slots=True)
class TempVoiceService:
    """Service métier pour la gestion des salons vocaux temporaires."""

    def find_parent_of_active(self, guild_id: int, channel_id: int) -> int | None:
        """Retourne l'identifiant du parent associé à un salon vocal temporaire actif."""
        return temp_voice_repo.tv_find_parent_of_active(guild_id, channel_id)
    
    def remove_active(self, guild_id: int, parent_channel_id: int, channel_id: int) -> None:
        """Supprime un salon vocal temporaire de la liste des salons actifs."""
        return temp_voice_repo.tv_remove_active(guild_id, parent_channel_id, channel_id)
    
    def get_parent(self, guild_id: int, parent_channel_id: int) -> int | None:
        """Récupère la limite d'utilisateurs configurée pour un parent de salons temporaires."""
        return temp_voice_repo.tv_get_parent(guild_id, parent_channel_id)
    
    def add_active(self, guild_id: int, parent_channel_id: int, channel_id: int) -> None:
        """Ajoute un salon vocal temporaire à la liste des salons actifs."""
        return temp_voice_repo.tv_add_active(guild_id, parent_channel_id, channel_id)
    
    def upsert_parent(self, guild_id: int, parent_channel_id: int, user_limit: int) -> None:
        """Crée ou met à jour la configuration d'un parent de salons vocaux temporaires."""
        return temp_voice_repo.tv_upsert_parent(guild_id, parent_channel_id, user_limit)
    
    def delete_parent(self, guild_id: int, parent_channel_id: int) -> None:
        """Supprime la configuration d'un parent de salons vocaux temporaires."""
        return temp_voice_repo.tv_delete_parent(guild_id, parent_channel_id)
    
    def list_parents(self, guild_id: int) -> list[tuple[int, int]]:
        """Liste tous les parents de salons vocaux temporaires configurés pour un serveur."""
        return temp_voice_repo.tv_list_parents(guild_id)
    
    def list_active_all(self, guild_id: int) -> list[tuple[int, int]]:
        """Liste tous les salons vocaux temporaires actifs d'un serveur (parent_channel_id, channel_id)."""
        return temp_voice_repo.tv_list_active_all(guild_id)
