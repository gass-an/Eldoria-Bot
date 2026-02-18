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