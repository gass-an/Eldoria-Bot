import asyncio
import sqlite3
from typing import Final

import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, time, timezone

from .utils import discord_utils

# Modules du projet (refactorisés)
from .features import embedGenerator, xp_system
from .db import gestionDB
from .json_tools import gestionJson
from .pages import gestionPages
from .utils.db_validation import is_valid_sqlite_db


# --------------------------- Récupération des infos dans le .env  (Token / ids) ---------------------
load_dotenv()
TOKEN: Final[str] = os.getenv('discord_token')

# Pour save
MY_ID: Final[int] = int(os.getenv('my_id'))
SAVE_GUILD_ID: Final[int] = int(os.getenv('guild_for_save'))
SAVE_CHANNEL_ID: Final[int] = int(os.getenv('channel_for_save')) 

# ------------------------------------ Initialisation du bot  ----------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # NOQA
intents.guilds = True
intents.members = True
bot = commands.Bot(intents=intents)


# ------------------------------------ Démarrage du bot  ---------------------------------------------
@bot.event
async def on_ready():
    try:
        # Synchronisation des commandes globales
        await bot.sync_commands()
        print("\nLes commandes globales ont été synchronisées.")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")
    print("Initialisation de la base de données si nécessaire.")
    gestionDB.init_db()
    
    print("Suppression en base des channels temporaires inexistant")
    for guild in bot.guilds:
        rows = gestionDB.tv_list_active_all(guild.id)
        for parent_id, channel_id in rows:
            if guild.get_channel(channel_id) is None:
                gestionDB.tv_remove_active(guild.id, parent_id, channel_id)
    print(f"{bot.user} est en cours d'exécution !\n")


# ------------------------------------ Gestion des rôles  --------------------------------------------
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member == bot.user:
        return
    
    role = False 
    role_id = gestionDB.rr_get_role_id(payload.guild_id, payload.message_id, payload.emoji.name)
    if role_id is None:
        return
    role = guild.get_role(role_id)

    if role and member:
        await member.add_roles(role)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    role = False
    guild = bot.get_guild(payload.guild_id)
    role_id = gestionDB.rr_get_role_id(payload.guild_id, payload.message_id, payload.emoji.name)
    
    if role_id is None:
        return
    
    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)

    if role and member:
        await member.remove_roles(role)


# ------------------------------------ Gestion des messages ------------------------------------------

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Ignore les MP
    if message.guild is None:
        return

    user_message = message.content or ""

    # XP: on compte aussi les messages avec pièces jointes (même sans texte)
    try:
        if user_message or message.attachments:
            await xp_system.handle_message_xp(message)
    except Exception as e:
        print(f"[XP] Erreur handle message: {e}")
    
    guild_id = message.guild.id
    channel_id = message.channel.id
    
    secret_role, role_id = embedGenerator.secret_role(
        user_message=user_message,
        guild_id=guild_id, 
        channel_id=channel_id
        )
    
    
    if secret_role:
        await message.delete()
        guild = bot.get_guild(guild_id)
        role = guild.get_role(role_id)
        await message.author.add_roles(role)



# ------------------------------------ Gestion des salons vocaux -------------------------------------
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild

    # 1) DELETE d'abord : si on quitte un salon temporaire et qu'il devient vide
    if before.channel:
        parent_id = gestionDB.tv_find_parent_of_active(guild.id, before.channel.id)
        if parent_id is not None and len(before.channel.members) == 0:
            await before.channel.delete()
            gestionDB.tv_remove_active(guild.id, parent_id, before.channel.id)

    # 2) GARDE-FOU : si on arrive déjà dans un salon temporaire, on ne crée rien
    if after.channel:
        if gestionDB.tv_find_parent_of_active(guild.id, after.channel.id) is not None:
            return

        # 3) CREATE : uniquement si after.channel est un "parent" configuré
        user_limit = gestionDB.tv_get_parent(guild.id, after.channel.id)
        if user_limit is not None:
            category = after.channel.category
            new_channel_name = f"Salon de {member.display_name}"
            overwrites = {
                member: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
            }

            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category,
                overwrites=overwrites,
                bitrate=after.channel.bitrate,
                user_limit=user_limit,
            )

            # Important : enregistrer AVANT le move pour que le 2e event (move) soit filtré
            gestionDB.tv_add_active(guild.id, after.channel.id, new_channel.id)

            await member.move_to(new_channel)




# ------------------------------------ Commandes du bot  ---------------------------------------------

@bot.slash_command(name="help", description="Affiche la liste des commandes disponible avec le bot")
async def help(interaction: discord.Interaction):
    help_infos = gestionJson.load_help_json()

    # Map: "ping" -> cmd object (slash)
    cmd_map = {c.name: c for c in bot.application_commands}

    member_perms = interaction.user.guild_permissions

    async def is_command_visible(cmd_name: str) -> bool:
        cmd = cmd_map.get(cmd_name)
        if cmd is None:
            # Commande présente dans help.json mais pas chargée sur le bot
            return False

        # 1) Filtre rapide sur les default_permissions (si présents)
        dp = getattr(cmd, "default_member_permissions", None)
        if dp is not None:
            # il faut que l'user ait tous les bits requis
            if (member_perms.value & dp.value) != dp.value:
                return False

        # 2) Filtre sur les checks Python (@commands.has_permissions, etc.)
        try:
            can = await cmd.can_run(interaction)
            if not can:
                return False
        except Exception:
            return False

        return True

    # Filtrer le help.json en gardant l’ordre
    filtered = {}
    for name, desc in help_infos.items():
        if await is_command_visible(name):
            filtered[name] = desc

    list_help_info = list(filtered.items())

    # Si rien n’est accessible, message clean
    if not list_help_info:
        await interaction.response.send_message(
            "Aucune commande disponible avec vos permissions.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    paginator = gestionPages.Paginator(
        items=list_help_info,
        embed_generator=embedGenerator.generate_help_embed,
        identifiant_for_embed=None,
        bot=None
    )
    embed, files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator, ephemeral=True)


# /ping (répond : Pong!) 
@bot.slash_command(name="ping",description="Ping-pong (pour vérifier que le bot est bien UP !)")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(content="Pong !")


# ---------- XP system ----------
def _level_label(guild: discord.Guild, role_ids: dict[int, int], level: int) -> str:
    """Retourne un label humain pour un niveau: mention du rôle si possible, sinon 'lvlX'."""
    rid = role_ids.get(level)
    role = guild.get_role(rid) if rid else None
    return role.mention if role else f"lvl{level}"

@bot.slash_command(name="xp_enable", description="(Admin) Active le système d'XP sur ce serveur.")
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_enable(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return
    
    await xp_system.ensure_guild_xp_setup(guild)
    # Crée config + niveaux si besoin, puis active
    gestionDB.xp_set_config(guild.id, enabled=True)

    await interaction.followup.send(content="✅ Système d'XP **activé** sur ce serveur.")


@bot.slash_command(name="xp_disable", description="(Admin) Désactive le système d'XP sur ce serveur.")
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_disable(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return

    gestionDB.xp_ensure_defaults(guild.id)
    gestionDB.xp_set_config(guild.id, enabled=False)

    await interaction.followup.send(content="⛔ Système d'XP **désactivé** sur ce serveur.")


@bot.slash_command(name="xp_status", description="Affiche l'état du système d'XP sur ce serveur.")
async def xp_status(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "Commande uniquement disponible sur un serveur.",
            ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    
    cfg = gestionDB.xp_get_config(guild.id)

    embed, files = await embedGenerator.generate_xp_status_embed(cfg=cfg, guild_id=guild.id, bot=bot)

    await interaction.followup.send(embed=embed, files=files, ephemeral=True)

@bot.slash_command(name="xp", description="Affiche ton XP et ton niveau.")
async def xp_me(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return

    guild = interaction.guild
    guild_id = guild.id
    user = interaction.user
    user_id = user.id

    if not gestionDB.xp_is_enabled(guild_id):
        embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, bot)
        await interaction.followup.send(embed=embed, files=files, ephemeral=True)
        return

    gestionDB.xp_ensure_defaults(guild_id)

    xp, _ = gestionDB.xp_get_member(guild_id, user_id)
    levels = gestionDB.xp_get_levels(guild_id)
    lvl = xp_system.compute_level(xp, levels)

    role_ids = gestionDB.xp_get_role_ids(guild_id)
    lvl_label = _level_label(guild, role_ids, lvl)

    # Prochain seuil
    next_req = None
    next_label = None
    for level, req in levels:
        if level == lvl + 1:
            next_req = req
            next_label = _level_label(guild, role_ids, lvl + 1)
            break

    embed, files = await embedGenerator.generate_xp_profile_embed(
        guild_id=guild_id,
        user=user,
        xp=xp,
        level=lvl,
        level_label=lvl_label,
        next_level_label=next_label,
        next_xp_required=next_req,
        bot=bot,
    )

    await interaction.followup.send(embed=embed, files=files, ephemeral=True)


@bot.slash_command(name="xp_roles", description="Affiche les rôles des niveaux et l'XP requis pour les obtenir.")
async def xp_roles(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Commande uniquement disponible sur un serveur.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    guild_id = guild.id

    if not gestionDB.xp_is_enabled(guild_id):
        embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, bot)
        await interaction.followup.send(embed=embed, files=files, ephemeral=True)
        return

    # S'assure que la config + niveaux + rôles existent
    gestionDB.xp_ensure_defaults(guild_id)

    levels_with_roles = gestionDB.xp_get_levels_with_roles(guild_id)
    embed, files = await embedGenerator.generate_xp_roles_embed(levels_with_roles, guild_id, bot)
    await interaction.followup.send(embed=embed, files=files, ephemeral=True)


@bot.slash_command(name="xp_list", description="Liste les XP des membres (classement).")
async def xp_list(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Commande uniquement disponible sur un serveur.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    guild_id = guild.id

    if not gestionDB.xp_is_enabled(guild_id):
        embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, bot)
        await interaction.followup.send(embed=embed, files=files, ephemeral=True)
        return

    
    gestionDB.xp_ensure_defaults(guild_id)

    rows = gestionDB.xp_list_members(guild_id, limit=200, offset=0)
    levels = gestionDB.xp_get_levels(guild_id)
    role_ids = gestionDB.xp_get_role_ids(guild_id)

    items = []
    for (uid, xp) in rows:
        lvl = xp_system.compute_level(xp, levels)
        lvl_label = _level_label(guild, role_ids, lvl)
        items.append((uid, xp, lvl, lvl_label))  # <- on ajoute label

    paginator = gestionPages.Paginator(
        items=items,
        embed_generator=embedGenerator.generate_list_xp_embed,  # à adapter pour lire lvl_label
        identifiant_for_embed=guild_id,
        bot=bot,
    )
    embed, files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


@bot.slash_command(name="xp_set_level", description="(Admin) Définit l'XP requis pour un niveau.")
@discord.option("level", int, description="Niveau (1..5)", min_value=1, max_value=5)
@discord.option("xp_required", int, description="XP requis pour atteindre ce niveau", min_value=0)
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_set_level(interaction: discord.Interaction, level: int, xp_required: int):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return

    gestionDB.xp_ensure_defaults(guild.id)
    gestionDB.xp_set_level_threshold(guild.id, level, xp_required)

    role_ids = gestionDB.xp_get_role_ids(guild.id)
    lvl_label = _level_label(guild, role_ids, level)

    await interaction.followup.send(content=f"✅ Seuil mis à jour : **{lvl_label}** = **{xp_required} XP**.")

    # Resync roles (best effort)
    try:
        for m in guild.members:
            await xp_system.sync_member_level_roles(guild, m)
    except Exception:
        pass


@bot.slash_command(name="xp_set_config", description="(Admin) Configure le gain d'XP par message et le cooldown.")
@discord.option("points_per_message", int, description="XP gagné par message (>=0)", min_value=0, max_value=1000)
@discord.option("cooldown_seconds", int, description="Cooldown en secondes entre 2 gains", min_value=0, max_value=3600)
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_set_config(interaction: discord.Interaction, points_per_message: int, cooldown_seconds: int):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return

    gestionDB.xp_ensure_defaults(guild.id)
    gestionDB.xp_set_config(guild.id, points_per_message=points_per_message, cooldown_seconds=cooldown_seconds)
    await interaction.followup.send(content=
        f"✅ Config XP mise à jour : **{points_per_message} XP**/message, cooldown **{cooldown_seconds}s**."
    )


@bot.slash_command(name="xp_set_bonus", description="(Admin) Définit le bonus d'XP appliqué si le membre affiche le tag du serveur sur son profil.")
@discord.option("bonus_percent", int, description="Bonus en % (0 pour désactiver)", min_value=0, max_value=300)
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_set_bonus(interaction: discord.Interaction, bonus_percent: int):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return

    gestionDB.xp_ensure_defaults(guild.id)
    gestionDB.xp_set_config(guild.id, bonus_percent=bonus_percent)

    await interaction.followup.send(content=
        f"✅ Bonus XP lié au tag du serveur mis à **{bonus_percent}%**."
    )

@bot.slash_command(name="xp_modify", description="(Admin) Ajoute/retire des XP à un membre.")
@discord.option("member", discord.Member, description="Membre à modifier")
@discord.option("delta", int, description="Nombre d'XP à ajouter (négatif = retirer)")
@discord.default_permissions(manage_guild=True)
@commands.has_permissions(manage_guild=True)
async def xp_modify(interaction: discord.Interaction, member: discord.Member, delta: int):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(content="Commande uniquement disponible sur un serveur.")
        return
    if member.bot:
        await interaction.followup.send(content="❌ Impossible de modifier l'XP d'un bot.")
        return

    gestionDB.xp_ensure_defaults(guild.id)
    new_xp = gestionDB.xp_add_xp(guild.id, member.id, delta)
    levels = gestionDB.xp_get_levels(guild.id)
    lvl = xp_system.compute_level(new_xp, levels)

    await xp_system.sync_member_level_roles(guild, member, xp=new_xp)

    role_ids = gestionDB.xp_get_role_ids(guild.id)
    lvl_label = _level_label(guild, role_ids, lvl)

    await interaction.followup.send(content=
        f"✅ {member.mention} est maintenant à **{new_xp} XP** (**{lvl_label}**)."
    )



# ---------- Reactions Roles ----------

@bot.slash_command(name="add_reaction_role", description="Associe une réaction sur un message défini à un rôle.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@discord.option("emoji", str, description="L'émoji de la réaction.")
@discord.option("role", discord.Role, description="Le rôle attribué.")
@discord.default_permissions(manage_roles=True)
@commands.has_permissions(manage_roles=True)
async def add_reaction_role(interaction: discord.Interaction, message_link: str, emoji: str, role: discord.Role):  

    await interaction.response.defer(ephemeral=True)
    guild_id, channel_id, message_id = discord_utils.extract_id_from_link(message_link)    

    if guild_id != interaction.guild.id:
        await interaction.followup.send(content=f"Le lien que vous m'avez fourni provient d'un autre serveur.")
        return

    guild = interaction.guild
    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    bot_highest_role = max(guild.me.roles, key=lambda r: r.position)
    if role.position >= bot_highest_role.position:
        await interaction.followup.send(content=f"Je ne peux pas attribuer le rôle <@&{role.id}> car il est au-dessus de mes permissions.")
        return

    existing = gestionDB.rr_list_by_message(guild_id, message_id)  # dict: {emoji: role_id}

    for existing_emoji, existing_role_id in existing.items():
        if existing_role_id == role.id and existing_emoji != emoji:
            await interaction.followup.send(content=f"Le rôle <@&{role.id}> est déjà associé à l'emoji {existing_emoji} sur le même message.")
            return
        if existing_role_id != role.id and existing_emoji == emoji:
            existing_role = guild.get_role(existing_role_id)
            await interaction.followup.send(content=f"L'emoji {existing_emoji} est déjà associé au rôle `{existing_role}` sur le même message.")
            return

    try:
        bot_member = guild.get_member(bot.user.id)
        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
        await message.add_reaction(emoji)
    except discord.NotFound:
        await interaction.followup.send(content="Message ou canal introuvable.")
        return
    except discord.Forbidden:
        await interaction.followup.send(content=(
            "## Un problème est survenu : \n"
            "- Soit je n'ai pas le droit de rajouter une réaction sur ce message.\n"
            "- Soit je n'ai pas le droit de gérer ce rôle."
            ))
        return

    gestionDB.rr_upsert(guild_id, message_id, emoji, role.id)

    await interaction.followup.send(content=f"## La réaction {emoji} est bien associée au rôle <@&{role.id}> sur le message sélectionné ! \n**Message :**\n {message.content}")


@bot.slash_command(name="remove_all_reactions", description="Retire toutes les réaction d'un message.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@discord.default_permissions(manage_roles=True, manage_messages=True)
@commands.has_permissions(manage_roles=True, manage_messages=True)
async def remove_all_reactions(interaction: discord.Interaction, message_link: str):  
    await interaction.response.defer(ephemeral=True)
    guild_id, channel_id, message_id = discord_utils.extract_id_from_link(message_link)    
    if guild_id != interaction.guild.id:
        await interaction.followup.send(content=
            f"Le lien que vous m'avez fourni provient d'un autre serveur."
            )
        return

    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)
    
    gestionDB.rr_delete_message(guild_id, message_id)

    try :
        await message.clear_reactions()
    except discord.Forbidden:
        await interaction.followup.send(content="Je n'ai pas la permission de supprimer les réactions.")
        return
    await interaction.followup.send(content=f"## Toutes les réactions ont été supprimées du message sélectionné.\n**Message** : \n{message.content}")


@bot.slash_command(name="remove_specific_reaction", description="Retire une réaction spécifique d'un message.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@discord.option("emoji", str, description="L'émoji de la réaction.")
@discord.default_permissions(manage_roles=True, manage_messages=True)
@commands.has_permissions(manage_roles=True, manage_messages=True)
async def remove_specific_reaction(interaction: discord.Interaction, message_link: str, emoji: str):
    await interaction.response.defer(ephemeral=True)
    guild_id, channel_id, message_id = discord_utils.extract_id_from_link(message_link)    
    if guild_id != interaction.guild.id:
        await interaction.followup.send(content=
            f"Le lien que vous m'avez fourni provient d'un autre serveur."
            )
        return
    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    gestionDB.rr_delete(guild_id, message_id, emoji)

    try:
        await message.clear_reaction(emoji)
    except discord.Forbidden:
        await interaction.followup.send(content="Je n'ai pas la permission de supprimer les réactions.")
        return
    await interaction.followup.send(content=f"## L'emoji {emoji} a bien été retiré du message.\n**Message** : \n{message.content}")


@bot.slash_command(name="list_of_reaction_roles", description="Affiche la liste des tous les rôles attribués avec une réaction à un message.")
@discord.default_permissions(manage_roles=True)
@commands.has_permissions(manage_roles=True)
async def list_reaction_roles(interaction: discord.Interaction):
    
    guild_id = interaction.guild.id
    role_config_guild_list = gestionDB.rr_list_by_guild_grouped(guild_id)
    
    await interaction.response.defer(ephemeral=True)
    paginator = gestionPages.Paginator(items=role_config_guild_list,embed_generator=embedGenerator.generate_list_roles_embed, identifiant_for_embed=guild_id, bot=bot)
    embed,files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


# ---------- Secrets Roles ------------

@bot.slash_command(name="add_secret_role", description="Attribue un role défini si l'utilisateur entre le bon message dans le bon channel.")
@discord.option("message", str, description="Le message exact pour que le rôle soit attribué.")
@discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
@discord.option("role", discord.Role, description="Le rôle attribué.")
@discord.default_permissions(manage_roles=True)
@commands.has_permissions(manage_roles=True)
async def add_secret_role(interaction: discord.Interaction, message: str, channel: discord.TextChannel, role: discord.Role):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    bot_highest_role = max(guild.me.roles, key=lambda r: r.position)
    if role.position >= bot_highest_role.position:
        await interaction.followup.send(content=f"Je ne peux pas attribuer le rôle <@&{role.id}> car il est au-dessus de mes permissions.")
        return

    guild_id = guild.id
    channel_id = channel.id
    message_str = str(message)

    existing_role_id = gestionDB.sr_match(guild_id, channel_id, message_str)
    if existing_role_id is not None and existing_role_id != role.id:
        await interaction.followup.send(
            content=f"Le message `{message_str}` est déjà associé au rôle <@&{existing_role_id}> dans le même channel."
        )
        return

    try:
        bot_member = guild.get_member(bot.user.id)
        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
    except discord.NotFound:
        await interaction.followup.send(content="Message ou canal introuvable.")
        return
    except discord.Forbidden:
        await interaction.followup.send(content=(
            "Je n'ai pas le droit de gérer ce rôle."
            ))
        return
    
    gestionDB.sr_upsert(guild_id, channel_id, message_str, role.id)

    await interaction.followup.send(content=f"Le rôle <@&{role.id}> est bien associée au message suivant : `{message}`")


async def message_secret_role_autocomplete(interaction: discord.AutocompleteContext):
    user_input = interaction.value.lower()
    guild_id = interaction.interaction.guild.id
    channel_id = interaction.options.get("channel")
    all_messages = gestionDB.sr_list_messages(guild_id=guild_id, channel_id=channel_id)
    return [message for message in all_messages if user_input in message.lower()][:25]


@bot.slash_command(name="delete_secret_role", description="Supprime l'attibution d'un secret_role déjà paramétré.")
@discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
@discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
@discord.default_permissions(manage_roles=True)
@commands.has_permissions(manage_roles=True)
async def delete_secret_role(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    await interaction.response.defer(ephemeral=True)

    guild_id = interaction.guild.id
    channel_id = channel.id
    message_str = str(message)

    # Vérifier si ça existe
    existing_role_id = gestionDB.sr_match(guild_id, channel_id, message_str)
    if existing_role_id is None:
        await interaction.followup.send(content=f"Aucune attribution trouvée pour le message `{message_str}` dans ce channel.")
        return

    # Supprimer en DB
    gestionDB.sr_delete(guild_id, channel_id, message_str)

    await interaction.followup.send(content=f"Le message `{message_str}` n'attribue plus de rôle")


@bot.slash_command(name="list_of_secret_roles", description="Affiche la liste des tous les rôles attribués avec un message secret.")
@discord.default_permissions(manage_roles=True)
@commands.has_permissions(manage_roles=True)
async def list_of_secret_roles(interaction: discord.Interaction):
    
    guild_id = interaction.guild.id
    secret_roles_guild_list = gestionDB.sr_list_by_guild_grouped(guild_id)

    
    await interaction.response.defer(ephemeral=True)
    paginator = gestionPages.Paginator(
        items=secret_roles_guild_list,
        embed_generator=embedGenerator.generate_list_secret_roles_embed,
        identifiant_for_embed=guild_id,
        bot=bot
        )
    embed,files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


# ------ Création salons vocaux -------

@bot.slash_command(name="init_creation_voice_channel", description="Défini le salon qui permettra à chacun de créer son propre salon vocal temporaire")
@discord.option("channel", discord.VoiceChannel, description="Le channel cible pour la création d'autres salon vocaux.")
@discord.option("user_limit", int, description="Le nombre de personnes qui pourront rejoindre les salons créés", min_value=1, max_value=99)
@discord.default_permissions(manage_channels=True)
@commands.has_permissions(manage_channels=True)
async def init_creation_voice_channel(interaction: discord.Interaction, channel: discord.VoiceChannel, user_limit: int):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    channel_id = channel.id
    gestionDB.tv_upsert_parent(guild_id, channel_id, user_limit)

    await interaction.followup.send(content=f"Le salon `{channel.name}` est désormais paramétré pour créer des salons pour {user_limit} personnes maximum")


@bot.slash_command(name="remove_creation_voice_channel",description="Désactive la création automatique de salons vocaux temporaires pour un salon donné")
@discord.option("channel", discord.VoiceChannel, description="Le salon parent à désactiver")
@discord.default_permissions(manage_channels=True)
@commands.has_permissions(manage_channels=True)
async def remove_creation_voice_channel(interaction: discord.Interaction,channel: discord.VoiceChannel):
    await interaction.response.send_message("Traitement en cours...", ephemeral=True)

    guild_id = interaction.guild.id
    channel_id = channel.id

    # Vérifie que le salon est bien un parent configuré
    if gestionDB.tv_get_parent(guild_id, channel_id) is None:
        await interaction.followup.send(
            content=f"❌ Le salon `{channel.name}` n'est pas configuré comme salon parent."
        )
        return

    gestionDB.tv_delete_parent(guild_id, channel_id)

    await interaction.followup.send(
        content=f"✅ Le salon `{channel.name}` n'est plus un salon de création automatique."
    )


@bot.slash_command(name="list_creation_voice_channels",description="Affiche la liste des salons parents qui créent des vocaux temporaires.")
@discord.default_permissions(manage_channels=True)
@commands.has_permissions(manage_channels=True)
async def list_creation_voice_channels(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    parents = gestionDB.tv_list_parents(guild_id)

    await interaction.response.defer(ephemeral=True)
    paginator = gestionPages.Paginator(
        items=parents,
        embed_generator=embedGenerator.generate_list_temp_voice_parents_embed,
        identifiant_for_embed=guild_id,
        bot=bot
    )
    embed, files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)



# -------------- Saves ----------------

@bot.slash_command(name="manual_save", description="Envoie la base SQLite (.db) dans un channel précis", guild_ids=[SAVE_GUILD_ID])
async def manual_save_command(interaction: discord.Interaction):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
        return

    await interaction.response.send_message("Sauvegarde en cours...", ephemeral=True)

    guild = bot.get_guild(SAVE_GUILD_ID)
    channel = guild.get_channel(SAVE_CHANNEL_ID)

    if not os.path.exists(gestionDB.DB_PATH):
        await channel.send("Fichier DB introuvable !")
        await interaction.followup.send(content="❌ DB introuvable.")
        return

    tmp_backup = "./temp_eldoria_backup.db"

    # Backup cohérent sous lock (aucun accès DB pendant)
    await asyncio.to_thread(gestionDB.backup_to_file, tmp_backup)

    filename = f"Eldoria_{datetime.now().strftime('%Y%m%d')}.db"
    with open(tmp_backup, "rb") as f:
        await channel.send(
            content="Sauvegarde du fichier SQLite suite à une demande.",
            file=discord.File(f, filename=filename)
        )

    try:
        os.remove(tmp_backup)
    except OSError:
        pass

    await interaction.followup.send(content="✅ DB bien envoyée !")

@bot.slash_command(name="insert_db",description="Remplace la base de données SQLite par celle fournie (message_id dans le channel de save)",guild_ids=[SAVE_GUILD_ID])
@discord.option("message_id", str, description="Id du message contenant le fichier .db")
async def insert_db_command(interaction: discord.Interaction, message_id: str):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
        return

    await interaction.response.send_message("Restauration en cours...", ephemeral=True)

    guild = bot.get_guild(SAVE_GUILD_ID)
    channel = guild.get_channel(SAVE_CHANNEL_ID)

    # Récupère le message et son attachment
    try:
        message = await channel.fetch_message(int(message_id))
    except Exception:
        await interaction.followup.send(content="❌ Message introuvable (vérifie l'ID).")
        return

    if not message.attachments:
        await interaction.followup.send(content="❌ Aucun fichier attaché sur ce message.")
        return

    attachment = message.attachments[0]

    # 🔒 Vérification réelle SQLite (extension + ouverture DB)
    if not await is_valid_sqlite_db(attachment):
        await interaction.followup.send(
            content="❌ Le fichier fourni n'est pas une base de données SQLite valide (.db)."
        )
        return

    tmp_new = f"./temp_{attachment.filename}"
    await attachment.save(tmp_new)

    # Remplace la DB sous lock (aucun accès DB pendant)
    try:
        await asyncio.to_thread(gestionDB.replace_db_file, tmp_new)
        # Optionnel : assure les tables si DB ancienne/vide
        gestionDB.init_db()
    except Exception as e:
        # Si replace échoue avant os.replace, on supprime le fichier temporaire
        try:
            if os.path.exists(tmp_new):
                os.remove(tmp_new)
        except OSError:
            pass
        await interaction.followup.send(content=f"❌ Erreur pendant la restauration : {e}")
        return

    # Si replace a réussi, tmp_new a été déplacé par os.replace -> rien à delete
    await interaction.followup.send(content="✅ Base de données remplacée avec succès.")




# ------------------------------------ Gestion des erreurs de permissions  ---------------------------

async def _reply_ephemeral(interaction: discord.Interaction, content: str):
    # Si déjà répondu (defer/send), on passe par followup
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error):
    # Unwrap (pycord/discord.py wrap souvent les erreurs)
    err = getattr(error, "original", error)

    if isinstance(err, commands.MissingPermissions):
        missing = ", ".join(err.missing_permissions)
        await _reply_ephemeral(interaction, f"❌ Permissions manquantes : **{missing}**.")
        return

    if isinstance(err, commands.BotMissingPermissions):
        missing = ", ".join(err.missing_permissions)
        await _reply_ephemeral(interaction, f"❌ Il me manque des permissions : **{missing}**.")
        return

    if isinstance(err, commands.MissingRole):
        await _reply_ephemeral(interaction, "❌ Vous n'avez pas le rôle requis pour utiliser cette commande.")
        return

    if isinstance(err, commands.MissingAnyRole):
        await _reply_ephemeral(interaction, "❌ Vous n'avez aucun des rôles requis pour utiliser cette commande.")
        return

    if isinstance(err, commands.CheckFailure):
        await _reply_ephemeral(interaction, "❌ Vous ne pouvez pas utiliser cette commande.")
        return

    # Fallback générique (log + message propre)
    print(f"[CommandError] {type(err).__name__}: {err}")
    await _reply_ephemeral(interaction, "❌ Une erreur est survenue lors de l'exécution de la commande.")





def main():
    bot.run(TOKEN)

if __name__ == '__main__':
    pass