"""Module de définition des fonctions de conversion d'exceptions liées aux rôles en messages d'erreur "membre-friendly" pour l'interface utilisateur."""
from eldoria.exceptions import role as exc


def role_error_message(e: exc.RoleError) -> str:
    """Retourne un message d'erreur "membre-friendly" à partir d'une exception de rôle."""
    match e:
        case exc.InvalidLink():
            return "❌ Le lien fourni est invalide."
        
        case exc.InvalidGuild():
            return "❌ Le lien que vous m'avez fourni provient d'un autre serveur."
        
        case exc.RoleAboveBot():
            return "❌ Je ne peux pas attribuer ce rôle car il est au-dessus de mes permissions."
        
        case exc.RoleAlreadyBound(emoji=emoji, role_id=rid, existing_emoji=ex_emoji) if ex_emoji is not None:
            return f"❌ Le rôle <@&{rid}> est déjà associé à l'emoji {ex_emoji} sur le même message."

        case exc.EmojiAlreadyBound(emoji=emoji, existing_role_id=ex_rid) if ex_rid is not None:
            return f"❌ L'emoji {emoji} est déjà associé au rôle <@&{ex_rid}> sur le même message."
        
        case exc.MessageAlreadyBound(message=msg, existing_role_id=rid):
            return f"❌ Le message `{msg}` est déjà associé au rôle <@&{rid}> dans le même channel."

        case exc.SecretRoleNotFound(message=msg):
            return f"❌ Aucune attribution trouvée pour le message `{msg}` dans ce channel."
        
        case _:
            # fallback: garde un message générique, pas le détail technique
            return "❌ Une erreur est survenue."
        