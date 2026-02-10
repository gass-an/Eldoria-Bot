from typing import cast

import discord

from eldoria.app.bot import EldoriaBot


async def message_secret_role_autocomplete(interaction: discord.AutocompleteContext):

    bot = cast(EldoriaBot, interaction.interaction.client)
    role = bot.services.role
    
    user_input = (interaction.value or "").lower()
    guild_id = interaction.interaction.guild.id
    channel_id = interaction.options.get("channel")
    
    all_messages = role.sr_list_messages(guild_id=guild_id, channel_id=channel_id)
    
    return [m for m in all_messages if user_input in m.lower()][:25]