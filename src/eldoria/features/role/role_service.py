from dataclasses import dataclass

from eldoria.db.repo import reaction_roles_repo, secret_roles_repo


@dataclass(slots=True)
class RoleService:
    """Service métier regroupant la gestion des rôles secrets et des rôles par réaction."""

    # ---------- Secret roles ----------

    def sr_match(self, guild_id: int, channel_id: int, phrase: str) -> int | None:
        """Retourne l'ID du rôle associé à une phrase secrète si elle existe."""
        return secret_roles_repo.sr_match(guild_id, channel_id, phrase)
    
    def sr_list_messages(self, guild_id: int, channel_id: int) -> list[str]:
        """Liste toutes les phrases secrètes configurées pour un salon."""
        return secret_roles_repo.sr_list_messages(guild_id, channel_id)
    
    def sr_upsert(self, guild_id: int, channel_id: int, phrase: str, role_id: int) -> None:
        """Crée ou met à jour une règle de rôle secret."""
        return secret_roles_repo.sr_upsert(guild_id, channel_id, phrase, role_id)
    
    def sr_delete(self, guild_id: int, channel_id: int, phrase: str) -> None:
        """Supprime une règle de rôle secret."""
        return secret_roles_repo.sr_delete(guild_id, channel_id, phrase)
    
    def sr_list_by_guild_grouped(self, guild_id: int) -> list[tuple[str, dict[str, int]]]:
        """Liste les rôles secrets d'un serveur, groupés par salon."""
        return secret_roles_repo.sr_list_by_guild_grouped(guild_id)

    # ---------- Reaction roles ----------

    def rr_upsert(self, guild_id: int, message_id: int, emoji: str, role_id: int) -> None:
        """Crée ou met à jour une règle de rôle par réaction."""
        return reaction_roles_repo.rr_upsert(guild_id, message_id, emoji, role_id)
    
    def rr_delete(self, guild_id: int, message_id: int, emoji: str) -> None:
        """Supprime une règle de rôle par réaction pour un emoji donné."""
        return reaction_roles_repo.rr_delete(guild_id, message_id, emoji)
    
    def rr_delete_message(self, guild_id: int, message_id: int) -> None:
        """Supprime toutes les règles de rôles par réaction associées à un message."""
        return reaction_roles_repo.rr_delete_message(guild_id, message_id)
    
    def rr_get_role_id(self, guild_id: int, message_id: int, emoji: str) -> int | None:
        """Retourne l'ID du rôle associé à un emoji sur un message."""
        return reaction_roles_repo.rr_get_role_id(guild_id, message_id, emoji)
    
    def rr_list_by_message(self, guild_id: int, message_id: int) -> dict[str, int]:
        """Liste les rôles par réaction d'un message sous forme {emoji: role_id}."""
        return reaction_roles_repo.rr_list_by_message(guild_id, message_id)
    
    def rr_list_by_guild_grouped(self, guild_id: int) -> list[tuple[str, dict[str, int]]]:
        """Liste les rôles par réaction d'un serveur, groupés par message."""
        return reaction_roles_repo.rr_list_by_guild_grouped(guild_id)
