import discord


def level_mention(guild: discord.Guild, level: int, role_ids: dict[int, int]) -> str:
    """Retourne la mention du rôle du niveau si configuré, sinon 'levelX'."""
    rid = role_ids.get(level) if role_ids else None
    role = guild.get_role(rid) if rid else None
    return role.mention if role else f"level{level}"


def level_label(guild: discord.Guild, role_ids: dict[int, int], level: int) -> str:
    """Retourne un label humain pour un niveau: mention du rôle si possible, sinon 'lvlX'."""
    rid = role_ids.get(level) if role_ids else None
    role = guild.get_role(rid) if rid else None
    return role.mention if role else f"lvl{level}"
