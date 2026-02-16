"""Module des embeds pour la bienvenue."""

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY


async def build_welcome_embed(guild_id: int, member: discord.Member, bot: EldoriaBot) -> tuple[discord.Embed, list[str]]:
    """Construit l'embed de bienvenue pour un nouvel arrivant."""
    guild = bot.get_guild(guild_id)
    if guild is None:
        raise RuntimeError(f"Guild {guild_id} not found")
    welcome = bot.services.welcome

    (title, msg, emojis) = welcome.get_welcome_message(
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