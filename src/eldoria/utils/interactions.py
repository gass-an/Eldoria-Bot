"""Utilitaires pour les interactions avec Discord, comme l'extraction d'IDs à partir de liens, la recherche de canaux, et la validation de contexte d'interaction."""

import discord


async def reply_ephemeral(interaction: discord.Interaction, content: str) -> None:
    """Répond en ephemeral en gérant defer/followup automatiquement."""
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)
