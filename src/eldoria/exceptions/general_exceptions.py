"""Module `general_exceptions`.

Contient des exceptions générales qui peuvent être utilisées dans différentes parties du bot pour signaler des erreurs courantes liées à l'interaction,
telles que des interactions provenant de sources inattendues ou des éléments requis qui sont introuvables ou invalides.
"""

class GuildRequired(Exception):
    """L'interaction doit provenir d'un serveur."""

class UserRequired(Exception):
    """L'interaction doit provenir d'un user."""

class ChannelRequired(Exception):
    """Le channel requis est introuvable ou invalide."""

class MessageRequired(Exception):
    """Le message requis est introuvable ou inaccessible."""