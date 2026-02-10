from typing import cast
import discord

from eldoria.app.bot import EldoriaBot


async def xp_level_role_autocomplete(interaction: discord.AutocompleteContext):
    guild = interaction.interaction.guild
    if guild is None:
        return []

    bot = cast(EldoriaBot, interaction.interaction.client)
    xp = bot.services.xp

    role_ids = xp.xp_get_role_ids(guild.id)
    if not role_ids:
        return []

    user_input = (interaction.value or "").lower()
    results = []

    for level, role_id in sorted(role_ids.items()):
        role = guild.get_role(role_id)
        if role is None:
            continue

        label = f"Level {level} — {role.name}"
        if user_input and user_input not in label.lower():
            continue

        results.append(label)
        if len(results) >= 25:
            break

    return results
