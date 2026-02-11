"""Module des embeds pour les vocaux temporaires."""

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate


async def build_list_temp_voice_parents_embed(
        items: list[tuple[int, int]], 
        page: int, 
        total_pages: int, 
        identifiant_for_embed: int,
        bot: EldoriaBot
    ) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed de la liste des salons parents pour les vocaux temporaires."""
    embed = discord.Embed(
        title="Salons pour la création de vocaux temporaires",
        description="Liste des salons configurés pour créer des salons vocaux temporaires.",
        color=EMBED_COLOUR_PRIMARY
    )
    embed.set_footer(text=f"Page {page+1}/{total_pages}")

    if not items:
        embed.add_field(name="Aucun salon", value="Aucun salon parent n'est configuré.", inline=False)
        decorate(embed, None, None)
        return embed, common_files(None, None)

    guild = bot.get_guild(identifiant_for_embed)

    lines = []
    for parent_channel_id, user_limit in items:
        channel = guild.get_channel(parent_channel_id) if guild else None
        if channel:
            lines.append(f"🔊 {channel.mention} — **limite**: `{user_limit}`")
        else:
            lines.append(f"⚠️ Salon introuvable (ID `{parent_channel_id}`) — **limite**: `{user_limit}`")

    embed.add_field(name="Salons configurés", value="\n".join(lines), inline=False)

    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files