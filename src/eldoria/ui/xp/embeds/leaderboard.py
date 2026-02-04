import discord
from discord.ext import commands

from eldoria.features.xp_system import get_xp_role_ids
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate


async def build_list_xp_embed(items, current_page: int, total_pages: int, guild_id: int, bot: commands.Bot):
    """Génère l'embed du classement XP.

    `items` peut être au format :
      - list[(user_id, xp, level)]
      - list[(user_id, xp, level, lvl_label)]  # si le label est pré-calculé côté commande
    """

    embed = discord.Embed(
        title="Classement XP",
        description="Liste des membres et de leurs XP.",
        colour=EMBED_COLOUR_PRIMARY,
    )

    guild = bot.get_guild(guild_id)

    # Récupère le mapping {level: role_id} depuis la DB (indépendant du nom)
    role_ids = get_xp_role_ids(guild_id) if guild_id else {}

    def level_label(level: int) -> str:
        if guild:
            rid = role_ids.get(int(level))
            role = guild.get_role(rid) if rid else None
            if role:
                return role.mention
        return f"lvl{level}"

    if not items:
        embed.add_field(name="Aucun membre", value="Personne n'a encore gagné d'XP.", inline=False)
    else:
        lines = []
        rank_start = current_page * 10 + 1
        for idx, item in enumerate(items, start=rank_start):
            # Compat: on accepte les tuples de taille 3 (ancien) ou 4 (avec label)
            if len(item) == 4:
                user_id, xp, level, lvl_txt = item
            else:
                user_id, xp, level = item
                lvl_txt = level_label(level)

            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"ID {user_id}"
            lines.append(f"**{idx}.** {name} — {lvl_txt} — **{xp} XP**")

        embed.add_field(name="Membres", value="\n".join(lines), inline=False)

    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files
