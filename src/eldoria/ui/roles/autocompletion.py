"""Module d'autocomplétion pour les rôles secrets."""

from typing import cast

import discord

from eldoria.app.bot import EldoriaBot


async def message_secret_role_autocomplete(
    interaction: discord.AutocompleteContext,
) -> list[str]:
    """Autocomplétion pour les messages de rôle secret."""
    bot = cast(EldoriaBot, interaction.interaction.client)
    role_service = bot.services.role

    guild = interaction.interaction.guild
    if guild is None:
        return []

    guild_id = guild.id

    channel_id_raw = interaction.options.get("channel")
    if not isinstance(channel_id_raw, int):
        return []

    channel_id = channel_id_raw

    user_input = (interaction.value or "").lower()

    all_messages = role_service.sr_list_messages(
        guild_id=guild_id,
        channel_id=channel_id,
    )

    return [m for m in all_messages if user_input in m.lower()][:25]