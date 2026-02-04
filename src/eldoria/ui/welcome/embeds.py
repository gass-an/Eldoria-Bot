import discord
from discord.ext import commands

from ...json_tools.welcome_json import getWelcomeMessage

from ..common.embeds.colors import EMBED_COLOUR_PRIMARY
from ..common.embeds.images import common_files, decorate


async def build_welcome_embed(guild_id: int, member: discord.Member, bot: commands.Bot):
    guild = bot.get_guild(guild_id)

    (title, msg, emojis) = getWelcomeMessage(
                guild_id,
                user=member.mention,
                server=guild.name,
                recent_limit=10,
            )

    embed = discord.Embed(
        title=f"{title}",
        description=f"\u200b\n{msg}\n\u200b",
        colour=EMBED_COLOUR_PRIMARY
    )

    embed.set_footer(text="✨ Bienvenue parmi nous.")

    embed.set_thumbnail(url=member.display_avatar.url)

    return embed, emojis