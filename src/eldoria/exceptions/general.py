"""Module `general_exceptions`.

Contient des exceptions générales qui peuvent être utilisées dans différentes parties du bot pour signaler des erreurs courantes liées à l'interaction,
telles que des interactions provenant de sources inattendues ou des éléments requis qui sont introuvables ou invalides.
"""

from eldoria.exceptions.base import AppError


class GuildRequired(AppError):
    """L'interaction doit provenir d'un serveur."""

class UserRequired(AppError):
    """L'interaction doit provenir d'un user."""

class ChannelRequired(AppError):
    """Le channel requis est introuvable ou invalide."""

class MessageRequired(AppError):
    """Le message requis est introuvable ou inaccessible."""

class MemberNotFound(AppError):
    """Le membre demandé est introuvable dans le serveur."""

    def __init__(self, guild_id: int, member_id: int) -> None:
        """Initialise l'exception avec les identifiants du serveur et du membre concernés."""
        super().__init__(f"Member {member_id} not found in guild {guild_id}.")
        self.guild_id = guild_id
        self.member_id = member_id

class GuildNotFound(AppError):
    """Le serveur demandé est introuvable (incohérence interne)."""

    def __init__(self, guild_id: int) -> None:
        """Initialise l'exception avec l'identifiant du serveur concerné."""
        super().__init__(f"Guild {guild_id} introuvable.")
        self.guild_id = guild_id

class InvalidMessageId(AppError):
    """L'identifiant de message fourni est invalide."""

class DatabaseRestoreError(AppError):
    """Erreur lors du remplacement de la base de données."""

class LogFileNotFound(AppError):
    """Le fichier de log est introuvable."""


class FeatureNotConfigured(AppError):
    """La fonctionnalité demandée n'est pas configurée pour ce serveur."""

    def __init__(self, feature: str) -> None:
        """Initialise l'exception avec le nom de la fonctionnalité concernée."""
        super().__init__(f"La fonctionnalité '{feature}' n'est pas configurée pour ce serveur.")
        self.feature = feature


class NotAllowed(AppError):
    """Action non autorisée dans le contexte actuel."""

class BotTargetNotAllowed(AppError):
    """Le membre ciblé est un bot."""

    def __init__(self, user_id: int) -> None:
        """Initialise l'exception avec l'identifiant de l'utilisateur ciblé qui est un bot."""
        super().__init__(f"Le membre ciblé ({user_id}) est un bot.")
        self.user_id = user_id
    pass

class XpDisabled(AppError):
    """Le système de XP est désactivé pour ce serveur."""

    def __init__(self, guild_id: int) -> None:
        """Initialise l'exception avec l'identifiant du serveur concerné."""
        super().__init__(f"Le système de XP est désactivé pour le serveur {guild_id}.")
        self.guild_id = int(guild_id)