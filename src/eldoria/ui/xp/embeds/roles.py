import discord

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate


async def build_xp_roles_embed(levels_with_roles, guild_id: int, bot: EldoriaBot):
    """Crée un embed listant les rôles liés aux niveaux et l'XP nécessaire.

    Paramètre attendu:
      levels_with_roles: list[(level:int, xp_required:int, role_id:int|None)]
    """
    embed = discord.Embed(
        title="Rôles & Niveaux XP",
        description="XP requis pour atteindre chaque rôle de niveau.",
        colour=EMBED_COLOUR_PRIMARY,
    )

    guild = bot.get_guild(guild_id) if guild_id else None

    lines = []
    for level, xp_required, role_id in levels_with_roles or []:
        role = guild.get_role(role_id) if (guild and role_id) else None
        role_txt = role.mention if role else f"lvl{level}"
        lines.append(f"**Niveau {level}** — {role_txt} — **{xp_required} XP**")

    if not lines:
        embed.add_field(name="Aucune configuration", value="Aucun niveau n'est configuré pour ce serveur.", inline=False)
    else:
        embed.add_field(name="Niveaux", value="\n".join(lines), inline=False)

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files
