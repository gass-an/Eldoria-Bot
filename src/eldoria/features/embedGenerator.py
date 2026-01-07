import discord
import asyncio

from ..db import gestionDB
from ..utils import discord_utils
from discord.ext import commands

async def generate_help_embed(list_of_tuple_title_description, current_page, total_pages, id, bot: commands.Bot):
    await asyncio.sleep(0.01)
    
    embed=discord.Embed(
            title="Liste des Commandes",
            description="Voici ci-dessous la liste de toutes les commandes disponible.",
            colour=discord.Color(0x00FFFF)
        )

    for element in list_of_tuple_title_description:
        embed.add_field(name='', value='',inline=False)
        embed.add_field(
            name=f"· /{element[0]} ",
            value=f"{element[1]}",
            inline=False
        )

    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = f"./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files =[thumbnail_file,image_file]
    return embed,files





async def generate_list_roles_embed(roles, current_page, total_pages, guild_id, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
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
    await asyncio.sleep(0.01)
    guild = bot.get_guild(guild_id)
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


def secret_role(user_message: str, guild_id: int, channel_id: int):
    role_id = gestionDB.sr_match(guild_id, channel_id, str(user_message))
    if role_id is None:
        return False, None
    return True, role_id


import discord

async def generate_list_temp_voice_parents_embed(items, page: int, total_pages: int, identifiant_for_embed: int, bot):
    """
    items: list[(parent_channel_id, user_limit)] pour la page courante
    identifiant_for_embed: guild_id
    """
    embed = discord.Embed(
        title="Salons pour la création de vocaux temporaires",
        description="Liste des salons configurés pour créer des salons vocaux temporaires.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Page {page+1}/{total_pages}")

    if not items:
        embed.add_field(name="Aucun salon", value="Aucun salon parent n'est configuré.", inline=False)
        return embed, []

    guild = bot.get_guild(identifiant_for_embed)

    lines = []
    for parent_channel_id, user_limit in items:
        channel = guild.get_channel(parent_channel_id) if guild else None
        if channel:
            lines.append(f"🔊 {channel.mention} — **limite**: `{user_limit}`")
        else:
            lines.append(f"⚠️ Salon introuvable (ID `{parent_channel_id}`) — **limite**: `{user_limit}`")

    embed.add_field(name="Salons configurés", value="\n".join(lines), inline=False)

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")
    
    files = [thumbnail_file, image_file]
    return embed, files


async def generate_list_xp_embed(items, current_page: int, total_pages: int, guild_id: int, bot: commands.Bot):
    """Génère l'embed du classement XP.

    `items` peut être au format :
      - list[(user_id, xp, level)]
      - list[(user_id, xp, level, lvl_label)]  # si le label est pré-calculé côté commande
    """
    await asyncio.sleep(0.01)

    embed = discord.Embed(
        title="Classement XP",
        description="Liste des membres et de leurs XP.",
        colour=discord.Color(0x00FFFF),
    )

    guild = bot.get_guild(guild_id)

    # Récupère le mapping {level: role_id} depuis la DB (indépendant du nom)
    role_ids = gestionDB.xp_get_role_ids(guild_id) if guild_id else {}

    def level_label(level: int) -> str:
        if guild:
            rid = role_ids.get(int(level))
            role = guild.get_role(rid) if rid else None
            if role:
                return role.mention
        return f"lvl{level}"

    if not items:
        embed.add_field(name="Aucun membre", value="Personne n'a encore gagné d'XP.", inline=False)
    else:
        lines = []
        rank_start = current_page * 10 + 1
        for idx, item in enumerate(items, start=rank_start):
            # Compat: on accepte les tuples de taille 3 (ancien) ou 4 (avec label)
            if len(item) == 4:
                user_id, xp, level, lvl_txt = item
            else:
                user_id, xp, level = item
                lvl_txt = level_label(level)

            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"ID {user_id}"
            lines.append(f"**{idx}.** {name} — {lvl_txt} — **{xp} XP**")

        embed.add_field(name="Membres", value="\n".join(lines), inline=False)

    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files


async def generate_xp_roles_embed(levels_with_roles, guild_id: int, bot: commands.Bot):
    """Crée un embed listant les rôles liés aux niveaux et l'XP nécessaire.

    Paramètre attendu:
      levels_with_roles: list[(level:int, xp_required:int, role_id:int|None)]
    """
    await asyncio.sleep(0.01)

    embed = discord.Embed(
        title="Rôles & Niveaux XP",
        description="XP requis pour atteindre chaque rôle de niveau.",
        colour=discord.Color(0x00FFFF),
    )

    guild = bot.get_guild(guild_id) if guild_id else None

    lines = []
    for level, xp_required, role_id in levels_with_roles or []:
        role = guild.get_role(role_id) if (guild and role_id) else None
        role_txt = role.mention if role else f"lvl{level}"
        lines.append(f"**Niveau {level}** — {role_txt} — **{xp_required} XP**")

    if not lines:
        embed.add_field(name="Aucune configuration", value="Aucun niveau n'est configuré pour ce serveur.", inline=False)
    else:
        embed.add_field(name="Niveaux", value="\n".join(lines), inline=False)

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files
