"""Module des embeds pour la version du bot."""

import discord

from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate
from eldoria.version import VERSION


async def build_version_embed() -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed de la version du bot."""
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