"""Module de définition des exceptions personnalisées liées aux rôles dans Eldoria Bot."""

from eldoria.exceptions.base import AppError


class RoleError(AppError):
    """Base de toutes les erreurs liées aux rôles."""

class InvalidLink(RoleError):
    """Le lien fourni est invalide ou ne correspond pas au format attendu."""
    
    def __init__(self) -> None:
        """Initialise l'exception avec un message indiquant que le lien est invalide."""
        super().__init__("Le lien fourni est invalide ou ne correspond pas au format attendu.")

class InvalidGuild(RoleError):
    """Le serveur spécifié n'est pas celui attendu."""

    def __init__(self, expected_guild_id: int, actual_guild_id: int) -> None:
        """Initialise l'exception avec un message indiquant que le serveur est invalide."""
        super().__init__(f"Le serveur spécifié (ID {actual_guild_id}) n'est pas celui attendu (ID {expected_guild_id}).")

class RoleAboveBot(RoleError):
    """Le rôle spécifié est au-dessus du rôle du bot, ce qui empêche le bot de le gérer."""

    def __init__(self, role_id: int) -> None:
        """Initialise l'exception avec un message indiquant que le rôle est au-dessus du rôle du bot."""
        super().__init__(f"Le rôle spécifié (ID {role_id}) est au-dessus du rôle du bot, ce qui empêche le bot de le gérer.")
        self.role_id = int(role_id)

class RoleAlreadyBound(RoleError):
    """Le rôle est déjà associé à un autre emoji sur ce message."""

    def __init__(self, *, message_id: int, role_id: int, existing_emoji: str) -> None:
        """Initialise l'exception avec un message indiquant que le rôle est déjà associé à un autre emoji sur ce message."""
        super().__init__(f"Le rôle spécifié (ID {role_id}) est déjà associé à l'emoji {existing_emoji} sur le même message (ID {message_id}).")
        self.message_id = int(message_id)
        self.role_id = int(role_id)
        self.existing_emoji = str(existing_emoji)


class EmojiAlreadyBound(RoleError):
    """L'emoji est déjà associé à un autre rôle sur ce message."""

    def __init__(self, *, message_id: int, emoji: str, existing_role_id: int) -> None:
        """Initialise l'exception avec un message indiquant que l'emoji est déjà associé à un autre rôle sur ce message."""
        super().__init__(f"L'emoji {emoji} est déjà associé au rôle (ID {existing_role_id}) sur le même message (ID {message_id}).")
        self.message_id = int(message_id)
        self.emoji = str(emoji)
        self.existing_role_id = int(existing_role_id)


class MessageAlreadyBound(RoleError):
    """Ce message est déjà associé à un autre rôle dans ce channel."""

    def __init__(self, *, message: str, existing_role_id: int) -> None:
        """Initialise l'exception avec un message indiquant que ce message est déjà associé à un autre rôle dans ce channel."""
        super().__init__(f"Le message `{message}` est déjà associé au rôle (ID {existing_role_id}) dans le même channel.")
        self.message = str(message)
        self.existing_role_id = int(existing_role_id)


class SecretRoleNotFound(RoleError):
    """Aucune règle secretrole trouvée pour ce message+channel."""

    def __init__(self, *, message: str) -> None:
        """Initialise l'exception avec un message indiquant qu'aucune règle secretrole n'a été trouvée pour ce message+channel."""
        super().__init__(f"Aucune règle secretrole trouvée pour le message `{message}` dans ce channel.")
        self.message = str(message)