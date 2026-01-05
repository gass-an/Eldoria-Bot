import asyncio
import sqlite3
from typing import Final
from dotenv import load_dotenv
import os, discord
from discord.ext import commands, tasks
from datetime import datetime, time, timezone
import fonctions, gestionDB, gestionJson, gestionPages, responses
from utils.db_validation import is_valid_sqlite_db


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
    gestionDB.init_db()
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
    user_message = message.content
    
    if not user_message:
        return
    
    guild_id = message.guild.id
    channel_id = message.channel.id
    
    secret_role, role_id = responses.secret_role(
        user_message=user_message,
        guild_id=guild_id, 
        channel_id=channel_id
        )
    
    
    if not secret_role:
        return
    await message.delete()
    guild = bot.get_guild(guild_id)
    role = guild.get_role(role_id)
    await message.author.add_roles(role)



# ------------------------------------ Gestion des salons vocaux -------------------------------------
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

    guild = member.guild
    # Pour créer les channels (SQLite)
    if after.channel:
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
                bitrate=after.channel.bitrate,  # Copiez la qualité audio du salon cible
                user_limit=user_limit, 
            )

            await member.move_to(new_channel)
            gestionDB.tv_add_active(guild.id, after.channel.id, new_channel.id)   

    # Pour delete les channels vides (SQLite)
    if before.channel:
        # Est-ce que ce salon est un salon temporaire créé par le bot ?
        parent_id = gestionDB.tv_find_parent_of_active(guild.id, before.channel.id)
        
        if parent_id is not None:
            # Il est bien géré par le système, on peut vérifier s'il est vide
            if len(before.channel.members) == 0:
                await before.channel.delete()
                gestionDB.tv_remove_active(guild.id, parent_id, before.channel.id)





# ------------------------------------ Commandes du bot  ---------------------------------------------

@bot.slash_command(name="help", description="Affiche la liste des commandes disponible avec le bot")
async def help(interaction: discord.Interaction):
    help_infos = gestionJson.load_help_json()
    list_help_info = list(help_infos.items())

    await interaction.response.defer()
    paginator = gestionPages.Paginator(items=list_help_info,embed_generator=responses.generate_help_embed, identifiant_for_embed=None, bot=None)
    embed,files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


# /ping (répond : Pong!) 
@bot.slash_command(name="ping",description="Ping-pong (pour vérifier que le bot est bien UP !)")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong !")


# ---------- Reactions Roles ----------

@bot.slash_command(name="add_reaction_role", description="Associe une réaction sur un message défini à un rôle.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@discord.option("emoji", str, description="L'émoji de la réaction.")
@discord.option("role", discord.Role, description="Le rôle attribué.")
@commands.has_permissions(manage_roles=True)
async def add_reaction_role(interaction: discord.Interaction, message_link: str, emoji: str, role: discord.Role):  

    await interaction.response.send_message("Votre demande est en cours de traitement...", ephemeral=True)
    guild_id, channel_id, message_id = fonctions.extract_id_from_link(message_link)    

    if guild_id != interaction.guild.id:
        await interaction.edit(content=f"Le lien que vous m'avez fourni provient d'un autre serveur.")
        return

    guild = interaction.guild
    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    bot_highest_role = max(guild.me.roles, key=lambda r: r.position)
    if role.position >= bot_highest_role.position:
        await interaction.edit(content=f"Je ne peux pas attribuer le rôle `{role.name}` car il est au-dessus de mes permissions.")
        return

    existing = gestionDB.rr_list_by_message(guild_id, message_id)  # dict: {emoji: role_id}

    for existing_emoji, existing_role_id in existing.items():
        if existing_role_id == role.id and existing_emoji != emoji:
            await interaction.edit(content=f"Le rôle `{role.name}` est déjà associé à l'emoji {existing_emoji} sur le même message.")
            return
        if existing_role_id != role.id and existing_emoji == emoji:
            existing_role = guild.get_role(existing_role_id)
            await interaction.edit(content=f"L'emoji {existing_emoji} est déjà associé au rôle `{existing_role}` sur le même message.")
            return

    try:
        bot_member = guild.get_member(bot.user.id)
        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
        await message.add_reaction(emoji)
    except discord.NotFound:
        await interaction.edit(content="Message ou canal introuvable.")
        return
    except discord.Forbidden:
        await interaction.edit(content=(
            "## Un problème est survenu : \n"
            "- Soit je n'ai pas le droit de rajouter une réaction sur ce message.\n"
            "- Soit je n'ai pas le droit de gérer ce rôle."
            ))
        return

    gestionDB.rr_upsert(guild_id, message_id, emoji, role.id)

    await interaction.edit(content=f"## La réaction {emoji} est bien associée au rôle `{role.name}` sur le message sélectionné ! \n**Message :**\n {message.content}")


@bot.slash_command(name="remove_all_reactions", description="Retire toutes les réaction d'un message.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@commands.has_permissions(manage_roles=True, manage_messages=True)
async def remove_all_reactions(interaction: discord.Interaction, message_link: str):  
    guild_id, channel_id, message_id = fonctions.extract_id_from_link(message_link)    
    if guild_id != interaction.guild.id:
        await interaction.response.send_message(
            f"Le lien que vous m'avez fourni provient d'un autre serveur.", 
            ephemeral=True
            )
        return

    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)
    
    gestionDB.rr_delete_message(guild_id, message_id)

    try :
        await message.clear_reactions()
    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas la permission de supprimer les réactions.", ephemeral=True)
        return
    await interaction.response.send_message(f"## Toutes les réactions ont été supprimées du message sélectionné.\n**Message** : \n{message.content}", ephemeral=True)


@bot.slash_command(name="remove_specific_reaction", description="Retire une réaction spécifique d'un message.")
@discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
@discord.option("emoji", str, description="L'émoji de la réaction.")
@commands.has_permissions(manage_roles=True, manage_messages=True)
async def remove_specific_reaction(interaction: discord.Interaction, message_link: str, emoji: str):
    guild_id, channel_id, message_id = fonctions.extract_id_from_link(message_link)    
    if guild_id != interaction.guild.id:
        await interaction.response.send_message(
            f"Le lien que vous m'avez fourni provient d'un autre serveur.", 
            ephemeral=True
            )
        return
    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    gestionDB.rr_delete(guild_id, message_id, emoji)

    try:
        await message.clear_reaction(emoji)
    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas la permission de supprimer les réactions.", ephemeral=True)
        return
    await interaction.response.send_message(f"## L'emoji {emoji} a bien été retiré du message.\n**Message** : \n{message.content}", ephemeral=True)


@bot.slash_command(name="list_of_reaction_roles", description="Affiche la liste des tous les rôles attribués avec une réaction à un message.")
@commands.has_permissions(manage_roles=True)
async def list_reaction_roles(interaction: discord.Interaction):
    
    guild_id = interaction.guild.id
    role_config_guild_list = gestionDB.rr_list_by_guild_grouped(guild_id)
    
    await interaction.response.defer()
    paginator = gestionPages.Paginator(items=role_config_guild_list,embed_generator=responses.generate_list_roles_embed, identifiant_for_embed=guild_id, bot=bot)
    embed,files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


# ---------- Secrets Roles ------------

@bot.slash_command(name="add_secret_role", description="Attribue un role défini si l'utilisateur entre le bon message dans le bon channel.")
@discord.option("message", str, description="Le message exact pour que le rôle soit attribué.")
@discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
@discord.option("role", discord.Role, description="Le rôle attribué.")
@commands.has_permissions(manage_roles=True)
async def add_secret_role(interaction: discord.Interaction, message: str, channel: discord.TextChannel, role: discord.Role):
    await interaction.response.send_message("Votre demande est en cours de traitement...", ephemeral=True)

    guild = interaction.guild
    bot_highest_role = max(guild.me.roles, key=lambda r: r.position)
    if role.position >= bot_highest_role.position:
        await interaction.edit(content=f"Je ne peux pas attribuer le rôle `{role.name}` car il est au-dessus de mes permissions.")
        return

    guild_id = guild.id
    channel_id = channel.id
    message_str = str(message)

    existing_role_id = gestionDB.sr_match(guild_id, channel_id, message_str)
    if existing_role_id is not None and existing_role_id != role.id:
        existing_role = guild.get_role(existing_role_id)
        await interaction.edit(
            content=f"Le message `{message_str}` est déjà associé au rôle `{existing_role}` dans le même channel."
        )
        return

    try:
        bot_member = guild.get_member(bot.user.id)
        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
    except discord.NotFound:
        await interaction.edit(content="Message ou canal introuvable.")
        return
    except discord.Forbidden:
        await interaction.edit(content=(
            "Je n'ai pas le droit de gérer ce rôle."
            ))
        return
    
    gestionDB.sr_upsert(guild_id, channel_id, message_str, role.id)

    await interaction.edit(content=f"Le rôle `{role.name}` est bien associée au message suivant : `{message}`")


async def message_secret_role_autocomplete(interaction: discord.AutocompleteContext):
    user_input = interaction.value.lower()
    guild_id = interaction.interaction.guild.id
    channel_id = interaction.options.get("channel")
    all_messages = gestionDB.sr_list_messages(guild_id=guild_id, channel_id=channel_id)
    return [message for message in all_messages if user_input in message.lower()][:25]


@bot.slash_command(name="delete_secret_role", description="Supprime l'attibution d'un secret_role déjà paramétré.")
@discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
@discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
@commands.has_permissions(manage_roles=True)
async def delete_secret_role(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    await interaction.response.send_message("Votre demande est en cours de traitement...", ephemeral=True)

    guild_id = interaction.guild.id
    channel_id = channel.id
    message_str = str(message)

    # Vérifier si ça existe
    existing_role_id = gestionDB.sr_match(guild_id, channel_id, message_str)
    if existing_role_id is None:
        await interaction.edit(content=f"Aucune attribution trouvée pour le message `{message_str}` dans ce channel.")
        return

    # Supprimer en DB
    gestionDB.sr_delete(guild_id, channel_id, message_str)

    await interaction.edit(content=f"Le message `{message_str}` n'attribue plus de rôle")


@bot.slash_command(name="list_of_secret_roles", description="Affiche la liste des tous les rôles attribués avec un message secret.")
@commands.has_permissions(manage_roles=True)
async def list_of_secret_roles(interaction: discord.Interaction):
    
    guild_id = interaction.guild.id
    secret_roles_guild_list = gestionDB.sr_list_by_guild_grouped(guild_id)

    
    await interaction.response.defer()
    paginator = gestionPages.Paginator(
        items=secret_roles_guild_list,
        embed_generator=responses.generate_list_secret_roles_embed,
        identifiant_for_embed=guild_id,
        bot=bot
        )
    embed,files = await paginator.create_embed()
    await interaction.followup.send(embed=embed, files=files, view=paginator)


# ------ Création salons vocaux -------

@bot.slash_command(name="init_creation_voice_channel", description="Défini le salon qui permettra à chacun de créer son propre salon vocal temporaire")
@discord.option("channel", discord.VoiceChannel, description="Le channel cible pour la création d'autres salon vocaux.")
@discord.option("user_limit", int, description="Le nombre de personnes qui pourront rejoindre les salons créés", min_value=1, max_value=99)
async def init_creation_voice_channel(interaction: discord.Interaction, channel: discord.VoiceChannel, user_limit: int):
    await interaction.response.send_message("Votre demande est en cours de traitement...", ephemeral=True)
    guild_id = interaction.guild.id
    channel_id = channel.id
    gestionDB.tv_upsert_parent(guild_id, channel_id, user_limit)

    await interaction.edit(content=f"Le salon `{channel.name}` est désormais paramétré pour créer des salons pour {user_limit} personnes maximum")




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
        await interaction.edit(content="❌ DB introuvable.")
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

    await interaction.edit(content="✅ DB bien envoyée !")

@bot.slash_command(
    name="insert_db",
    description="Remplace la base de données SQLite par celle fournie (message_id dans le channel de save)",
    guild_ids=[SAVE_GUILD_ID]
)
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
        await interaction.edit(content="❌ Message introuvable (vérifie l'ID).")
        return

    if not message.attachments:
        await interaction.edit(content="❌ Aucun fichier attaché sur ce message.")
        return

    attachment = message.attachments[0]

    # 🔒 Vérification réelle SQLite (extension + ouverture DB)
    if not await is_valid_sqlite_db(attachment):
        await interaction.edit(
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
        await interaction.edit(content=f"❌ Erreur pendant la restauration : {e}")
        return

    # Si replace a réussi, tmp_new a été déplacé par os.replace -> rien à delete
    await interaction.edit(content="✅ Base de données remplacée avec succès.")




# ------------------------------------ Gestion des erreurs de permissions  ---------------------------

# @bot.event
# async def on_application_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, commands.MissingRole):
#         await interaction.edit(
#             content="Vous n'avez pas le rôle requis pour utiliser cette commande."
#         )
#     else:
#         await interaction.edit(
#             content="Une erreur est survenue lors de l'exécution de la commande."
#         )


def main():
    bot.run(TOKEN)


if __name__ == '__main__':
    main()

