import discord

from ...version import VERSION
from .common.embedColors import EMBED_COLOUR_PRIMARY
from .common.embedImages import common_files, decorate


async def generate_version_embed():
    embed = discord.Embed(
        title="Eldoria",
        description="La version actuelle de votre bot préféré",
        colour=EMBED_COLOUR_PRIMARY
    )
    embed.add_field(
        name="Version",
        value=f"v{VERSION}",
        inline=True
    )
    embed.add_field(
        name="Statut",
        value="Développement stable",
        inline=True
    )

    embed.set_footer(text="Développé par Faucon98")

    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files