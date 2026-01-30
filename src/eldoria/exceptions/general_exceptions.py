class GuildRequired(Exception):
    """L'interaction doit provenir d'un serveur."""

class UserRequired(Exception):
    """L'interaction doit provenir d'un user."""

class ChannelRequired(Exception):
    """Le channel requis est introuvable ou invalide."""

class MessageRequired(Exception):
    """Le message requis est introuvable ou inaccessible."""