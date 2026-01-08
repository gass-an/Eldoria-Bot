import discord
from discord.ext import commands

from ...utils import discord_utils

async def generate_list_roles_embed(roles, current_page, total_pages, guild_id, bot: commands.Bot):
    nb_roles = 0
    embed = discord.Embed(
        title="Liste des rôles",
        description="Voici ci-dessous la liste de tous rôles attribués avec une réaction à un message.",
        colour=discord.Color(0x00FFFF)
    )

    for message_id in roles:
        # message_id = (message_id_str, {emoji: role_id})
        channel_id = await discord_utils.find_channel_id(bot=bot, message_id=message_id[0], guild_id=guild_id)
        nb_roles += len(message_id[1])

        list_roles = ""
        for existing_emoji, existing_role_id in message_id[1].items():
            list_roles += f"{existing_emoji}  **->** <@&{existing_role_id}>\n"

        if list_roles != "":
            embed.add_field(name='', value='', inline=False)
            embed.add_field(
                name=f"· https://discord.com/channels/{guild_id}/{channel_id}/{message_id[0]} : ",
                value=f"{list_roles}",
                inline=False
            )

    embed.set_footer(text=f"Nombre de rôles attribués : {nb_roles}\nPage {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files


async def generate_list_secret_roles_embed(roles, current_page, total_pages, guild_id, bot: commands.Bot):
    nb_roles = 0
    embed = discord.Embed(
        title="Liste des rôles secrets",
        description="Voici ci-dessous la liste de tous rôles attribués avec une phrase magique.",
        colour=discord.Color(0x00FFFF)
    )

    for channel_id in roles:
        # channel_id = (channel_id_str, {phrase: role_id})
        nb_roles += len(channel_id[1])

        list_roles = ""
        for existing_message, existing_role_id in channel_id[1].items():
            list_roles += f" Message: `{existing_message}`  **->** <@&{existing_role_id}>\n"

        if list_roles != "":
            embed.add_field(name='', value='', inline=False)
            embed.add_field(
                name=f"· https://discord.com/channels/{guild_id}/{channel_id[0]} : ",
                value=f"{list_roles}",
                inline=False
            )

    embed.set_footer(text=f"Nombre de rôles attribués : {nb_roles}\nPage {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files
