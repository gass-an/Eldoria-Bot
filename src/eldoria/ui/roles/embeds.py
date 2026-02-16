"""Module pour construire les embeds liés aux rôles."""

from collections.abc import Sequence

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate
from eldoria.utils.discord_utils import find_channel_id


async def build_list_roles_embed(
    roles: Sequence[tuple[str, dict[str, int]]],
    current_page: int,
    total_pages: int,
    guild_id: int,
    bot: EldoriaBot,
) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed de la liste des rôles attribués par réaction."""
    nb_roles: int = 0

    embed = discord.Embed(
        title="Liste des rôles",
        description="Voici ci-dessous la liste de tous rôles attribués avec une réaction à un message.",
        colour=EMBED_COLOUR_PRIMARY,
    )

    for message_id_str, emoji_to_role in roles:
        try:
            msg_id = int(message_id_str)
        except ValueError:
            continue

        channel_id: int | None = await find_channel_id(
            bot=bot,
            message_id=msg_id,
            guild_id=guild_id,
        )

        nb_roles += len(emoji_to_role)

        list_roles = ""
        for existing_emoji, existing_role_id in emoji_to_role.items():
            list_roles += f"{existing_emoji}  **->** <@&{existing_role_id}>\n"

        if list_roles:
            embed.add_field(name="", value="", inline=False)
            embed.add_field(
                name=f"· https://discord.com/channels/{guild_id}/{channel_id}/{msg_id} : ",
                value=list_roles,
                inline=False,
            )

    embed.set_footer(
        text=f"Nombre de rôles attribués : {nb_roles}\nPage {current_page + 1}/{total_pages}"
    )

    decorate(embed, None, None)
    files: list[discord.File] = common_files(None, None)

    return embed, files


async def build_list_secret_roles_embed(
    roles: Sequence[tuple[str, dict[str, int]]],
    current_page: int,
    total_pages: int,
    guild_id: int,
    bot: EldoriaBot,
) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed de la liste des rôles secrets."""
    nb_roles: int = 0

    embed = discord.Embed(
        title="Liste des rôles secrets",
        description="Voici ci-dessous la liste de tous rôles attribués avec une phrase magique.",
        colour=EMBED_COLOUR_PRIMARY,
    )

    for channel_id in roles:
        # channel_id = (channel_id_str, {phrase: role_id})
        nb_roles += len(channel_id[1])

        list_roles: str = ""
        for existing_message, existing_role_id in channel_id[1].items():
            list_roles += (
                f" Message: `{existing_message}`  **->** <@&{existing_role_id}>\n"
            )

        if list_roles != "":
            embed.add_field(name="", value="", inline=False)
            embed.add_field(
                name=f"· https://discord.com/channels/{guild_id}/{channel_id[0]} : ",
                value=f"{list_roles}",
                inline=False,
            )

    embed.set_footer(
        text=f"Nombre de rôles attribués : {nb_roles}\nPage {current_page + 1}/{total_pages}"
    )

    decorate(embed, None, None)
    files: list[discord.File] = common_files(None, None)

    return embed, files