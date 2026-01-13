import discord
from discord.ext import commands

from .common.embedColors import EMBED_COLOUR_PRIMARY
from .common.embedImages import common_files, decorate


async def generate_xp_disable_embed(guild_id: int, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
    embed = discord.Embed(
        title="Bienvenue",
        description="",
        colour=EMBED_COLOUR_PRIMARY
    )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files