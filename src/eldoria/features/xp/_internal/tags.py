"""Module de logique métier pour la fonctionnalité d'XP par message."""

import discord


def has_active_server_tag_for_guild(member: discord.abc.User, guild: discord.Guild) -> bool:
    """True si le membre affiche l'identité (Server Tag) de CETTE guilde sur son profil.

    Compatibilité: si la lib ne fournit pas ces champs, retourne False (pas de bonus plutôt que planter).
    """
    # Selon les versions/forks, primary_guild peut être sur User ou accessible via member._user
    user_obj = member
    pg = getattr(user_obj, "primary_guild", None)
    if pg is None:
        pg = getattr(getattr(member, "_user", None), "primary_guild", None)

    if pg is None:
        return False

    identity_enabled = bool(getattr(pg, "identity_enabled", False))
    if not identity_enabled:
        return False

    identity_guild_id = getattr(pg, "identity_guild_id", None)
    if identity_guild_id != guild.id:
        return False

    # Si la lib expose le tag côté guilde, on vérifie aussi l'égalité des tags
    guild_tag = getattr(guild, "tag", None)
    user_tag = getattr(pg, "tag", None)
    if guild_tag and user_tag:
        return str(user_tag).upper() == str(guild_tag).upper()

    return True
