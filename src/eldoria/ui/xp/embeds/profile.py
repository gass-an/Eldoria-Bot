import discord

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate


async def build_xp_profile_embed(
    *,
    guild_id: int,
    user: discord.User | discord.Member,
    xp: int,
    level: int,
    level_label: str,
    next_level_label: str | None,
    next_xp_required: int | None,
    bot: EldoriaBot,
    ):
    
    guild = bot.get_guild(guild_id)

    embed = discord.Embed(
        title="📊 Ton profil XP",
        colour=EMBED_COLOUR_PRIMARY
    )

    embed.set_author(
        name=user.display_name,
        icon_url=user.display_avatar.url if user.display_avatar else None
    )

    embed.add_field(
        name="Niveau actuel",
        value=f"**{level_label}** (niveau {level})",
        inline=True
    )

    embed.add_field(
        name="XP total",
        value=f"**{xp} XP**",
        inline=True
    )

    if next_xp_required is None:
        embed.add_field(
            name="Progression",
            value="🏆 **Niveau maximum atteint !**",
            inline=False
        )
    else:
        remaining = max(next_xp_required - xp, 0)
        embed.add_field(
            name="Prochain niveau",
            value=(
                f"**{next_level_label}**\n"
                f"Seuil : **{next_xp_required} XP**\n"
                f"XP restante : **{remaining} XP**"
            ),
            inline=False
        )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files