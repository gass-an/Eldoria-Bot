"""Module de mapping des exceptions générales de l'application en messages d'erreur destinés à être affichés dans l'interface utilisateur (UI)."""

from eldoria.exceptions import general as exc


def general_error_message(e: exc.AppError) -> str:
    """Retourne un message user-friendly pour les erreurs générales."""
    match e:
        case exc.GuildRequired():
            return "❌ Cette commande doit être utilisée sur un serveur."

        case exc.UserRequired():
            return "❌ Cette action doit être effectuée par un utilisateur."

        case exc.ChannelRequired():
            return "❌ Impossible de retrouver le salon associé à cette action."

        case exc.MessageRequired():
            return "❌ Le message associé à cette action est introuvable."
        
        case exc.MemberNotFound(guild_id=guild_id, member_id=member_id):
            return f"❌ Impossible de retrouver le membre {member_id} dans le serveur {guild_id}."
        
        case exc.DatabaseRestoreError():
            return "❌ Une erreur est survenue lors du remplacement de la base de données."
        
        case exc.GuildNotFound(guild_id=guild_id):
            return f"❌ Impossible de retrouver le serveur {guild_id}."
        
        case exc.InvalidMessageId():
            return "❌ L'identifiant de message fourni est invalide."

        case _:
            return "❌ Une erreur est survenue."