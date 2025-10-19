from typing import Final
from dotenv import load_dotenv
import os, discord, json
from discord.ext import commands, tasks
from datetime import datetime, time, timezone
import fonctions, gestionJson, gestionPages, responses


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
    fonctions.json_init()
    print(f"{bot.user} est en cours d'exécution !\n")


# ------------------------------------ Gestion des rôles  --------------------------------------------
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member == bot.user:
        return
    
    role = False 
    role_config = gestionJson.load_json("config_roles")
    role_config_guild = role_config[str(payload.guild_id)]

    if str(payload.message_id) in role_config_guild and payload.emoji.name in role_config_guild[str(payload.message_id)]:
        role_id = role_config_guild[str(payload.message_id)][payload.emoji.name]
        role = guild.get_role(role_id)

    if role and member:
            await member.add_roles(role)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    role = False
    role_config = gestionJson.load_json("config_roles")
    role_config_guild = role_config[str(payload.guild_id)]

    if str(payload.message_id) in role_config_guild and payload.emoji.name in role_config_guild[str(payload.message_id)]:
        guild = bot.get_guild(payload.guild_id)
        role_id = role_config_guild[str(payload.message_id)][payload.emoji.name]
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
    temp_channels = gestionJson.load_json("temp_channels")
    
 
    if str(guild.id) not in temp_channels:

        return
    temp_channels_guild = temp_channels[str(guild.id)]
    
    # Pour créer les channels
    if after.channel and (str(after.channel.id) in temp_channels_guild):

        temp_channels_channel = temp_channels_guild[str(after.channel.id)]
        user_limit = temp_channels_channel["user_limit"]

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
        temp_channels_channel["active_channel"].append(new_channel.id)
        gestionJson.save_json("temp_channels",temp_channels)    

    

    # Pour delete les channels vides

    all_parents_channel = []
    for channel_id, channel_info in temp_channels_guild.items():
        active_channels = channel_info.get("active_channel", [])

        for i in range(len(active_channels)):
            all_parents_channel.append(channel_id)

    
    if before.channel:
        if before.channel.id in active_channels:
            before_parent_channel_index = active_channels.index(before.channel.id)
            before_parent_channel = all_parents_channel[before_parent_channel_index]

            temp_channels_channel = temp_channels_guild[str(before_parent_channel)]

            if len(before.channel.members) == 0:
                await before.channel.delete()

                if before.channel.id in temp_channels_channel["active_channel"]:
                    temp_channels_channel["active_channel"].remove(before.channel.id)
                    gestionJson.save_json("temp_channels",temp_channels)




# ------------------------------------ Commandes du bot  ---------------------------------------------

@bot.slash_command(name="help", description="Affiche la liste des commandes disponible avec le bot")
async def help(interaction: discord.Interaction):
    help_infos = gestionJson.load_json("help")
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

    role_config = gestionJson.load_json("config_roles")

    if str(guild_id) not in role_config:
        role_config[str(guild_id)] = {}
    
    role_config_guild = role_config[str(guild_id)]
    
    if str(message_id) not in role_config_guild:
        role_config_guild[str(message_id)] = {}
    

    for existing_emoji, existing_role_id in role_config_guild[str(message_id)].items():
        if existing_role_id == role.id and existing_emoji != emoji:
            await interaction.edit(content=f"Le rôle `{role.name}` est déjà associé à l'emoji {existing_emoji} sur le même message.")
            return
        if existing_role_id != role.id and existing_emoji == emoji:
            existing_role = guild.get_role(existing_role_id)
            await interaction.edit(content=f"L'emoji {existing_emoji} est déjà associé au rôle `{existing_role}` sur le même message.")
            return
    
    role_config_guild[str(message_id)][emoji] = role.id


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

    gestionJson.save_json("config_roles",role_config)

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
    
    role_config = gestionJson.load_json("config_roles")
    role_config_guild = role_config[str(guild_id)]
    
    if str(message_id) in role_config_guild:
        del role_config_guild[str(message_id)]
    
    gestionJson.save_json("config_roles", role_config)
    
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

    role_config = gestionJson.load_json("config_roles")
    role_config_guild = role_config[str(guild_id)]

    if str(message_id) in role_config_guild:
        if emoji in role_config_guild[str(message_id)]:
            del role_config_guild[str(message_id)][emoji]
            gestionJson.save_json("config_roles", role_config)
    

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
    role_config = gestionJson.load_json("config_roles")
    if str(guild_id) in role_config:
        role_config_guild = role_config[str(guild_id)]
        role_config_guild_list = list(role_config_guild.items())
    else :
        role_config_guild_list = []
    
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
    secret_roles = gestionJson.load_json("config_secret_roles")

    if str(guild_id) not in secret_roles:
        secret_roles[str(guild_id)] = {}
    secret_roles_guild = secret_roles[str(guild_id)]

    if str(channel_id) not in secret_roles_guild:
        secret_roles_guild[str(channel_id)] = {}
    secret_roles_channel = secret_roles_guild[str(channel_id)]

    for existing_message, existing_role_id in secret_roles_channel.items():
        if existing_role_id != role.id and existing_message == str(message):
            await interaction.edit(content=f"Le message {message} est déjà associé au rôle `{role.name}` dans le même channel.")
            return

    secret_roles_channel[str(message)] = role.id

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
    
    gestionJson.save_json("config_secret_roles", secret_roles)

    await interaction.edit(content=f"Le rôle `{role.name}` est bien associée au message suivant : `{message}`")


async def message_secret_role_autocomplete(interaction: discord.AutocompleteContext):
    user_input = interaction.value.lower()
    guild_id = interaction.interaction.guild.id
    channel_id = interaction.options.get("channel")
    all_messages=gestionJson.get_messages_secret_role(guild_id=guild_id, channel_id=channel_id)
    return [message for message in all_messages if user_input in message.lower()][:25]


@bot.slash_command(name="delete_secret_role", description="Supprime l'attibution d'un secret_role déjà paramétré.")
@discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
@discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
@commands.has_permissions(manage_roles=True)
async def delete_secret_role(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    await interaction.response.send_message("Votre demande est en cours de traitement...", ephemeral=True)
    guild_id = interaction.guild.id
    channel_id = channel.id
    secret_roles = gestionJson.load_json("config_secret_roles")

    if str(guild_id) not in secret_roles:
        return
    secret_roles_guild = secret_roles[str(guild_id)]

    if str(channel_id) not in secret_roles_guild:
        return
    secret_roles_channel = secret_roles_guild[str(channel_id)]

    if message not in secret_roles_channel:
        return 
    del secret_roles_channel[message]

    gestionJson.save_json("config_secret_roles", secret_roles)

    await interaction.edit(content=f"Le message `{message}` n'attribue plus de rôle")


@bot.slash_command(name="list_of_secret_roles", description="Affiche la liste des tous les rôles attribués avec un message secret.")
@commands.has_permissions(manage_roles=True)
async def list_reaction_roles(interaction: discord.Interaction):
    
    guild_id = interaction.guild.id
    secret_roles = gestionJson.load_json("config_secret_roles")
    if str(guild_id) in secret_roles:
        secret_roles_guild = secret_roles[str(guild_id)]
        secret_roles_guild_list = list(secret_roles_guild.items())
    else :
        secret_roles_guild_list = []
    
    await interaction.response.defer()
    paginator = gestionPages.Paginator(items=secret_roles_guild_list,embed_generator=responses.generate_list_secret_roles_embed, identifiant_for_embed=guild_id, bot=bot)
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
    temp_channels = gestionJson.load_json("temp_channels")
    
    if str(guild_id) not in temp_channels:
        temp_channels[str(guild_id)] = {}
    temp_channels_guild = temp_channels[str(guild_id)]

    if str(channel_id) not in temp_channels_guild: 
        temp_channels_guild[str(channel_id)] = {
            "user_limit" : user_limit,
            "active_channel" : []
        }
    else : 
        temp_channels_guild[str(channel_id)]["user_limit"] = user_limit

    gestionJson.save_json("temp_channels", temp_channels)

    await interaction.edit(content=f"Le salon `{channel.name}` est désormais paramétré pour créer des salons pour {user_limit} personnes maximum")




# -------------- Saves ----------------

@bot.slash_command(name="manual_save", description="Envoie les json dans un channel précis", guild_ids=[SAVE_GUILD_ID])
async def manual_save_command(interaction: discord.Interaction):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
        return

    guild = bot.get_guild(SAVE_GUILD_ID)
    channel = guild.get_channel(SAVE_CHANNEL_ID)

    if os.path.exists("./json/config_roles.json"):

        with open("./json/config_roles.json", "rb") as file:
            await channel.send(
                content="Sauvegarde du fichier config_roles.json suite à une demande.",
                file=discord.File(file, filename=f"Config_roles_REACTION_{datetime.now().strftime('%Y%m%d')}.json")
            )
    else:
        await channel.send("Fichier config_roles.json introuvable !", ephemeral=True)


    if os.path.exists("./json/config_secret_roles.json"):

        with open("./json/config_secret_roles.json", "rb") as file:
            await channel.send(
                content="Sauvegarde du fichier config_secret_roles.json suite à une demande.",
                file=discord.File(file, filename=f"Config_roles_SECRET_{datetime.now().strftime('%Y%m%d')}.json")
            )
    else:
        await channel.send("Fichier config_secret_roles.json introuvable !", ephemeral=True)

    if os.path.exists("./json/temp_channels.json"):

        with open("./json/temp_channels.json", "rb") as file:
            await channel.send(
                content="Sauvegarde du fichier temp_channels.json suite à une demande.",
                file=discord.File(file, filename=f"temp_channels_{datetime.now().strftime('%Y%m%d')}.json")
            )
    else:
        await channel.send("Fichier temp_channels.json introuvable !", ephemeral=True)


    await interaction.response.send_message("Fichiers bien envoyés ! ", ephemeral=True)



@bot.slash_command(name="insert_config_roles_reaction", description="Remplace le config_roles.json par celui fourni",guild_ids=[SAVE_GUILD_ID])
@discord.option("message_id", str, description= "Id du message contenant le json")
async def insert_json_reaction_command(interaction: discord.Interaction, message_id: str ):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
    else:
        guild = bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID)
        message = await channel.fetch_message(message_id)
        attachment = message.attachments[0]
        
        file_path = f"./json/temp_{attachment.filename}"
        await attachment.save(file_path)


        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        file.close()


        with open('./json/config_roles.json', mode='w') as fichier:
            json.dump(data, fichier, indent=4)

        os.remove(file_path)
        await interaction.response.send_message("Le config_roles.json à bien été remplacé", ephemeral=True)


@bot.slash_command(name="insert_config_roles_secret", description="Remplace le config_secret_roles.json par celui fourni",guild_ids=[SAVE_GUILD_ID])
@discord.option("message_id", str, description= "Id du message contenant le json")
async def insert_json_secret_command(interaction: discord.Interaction, message_id: str ):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
    else:
        guild = bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID)
        message = await channel.fetch_message(message_id)
        attachment = message.attachments[0]
        
        file_path = f"./json/temp_{attachment.filename}"
        await attachment.save(file_path)


        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        file.close()


        with open('./json/config_secret_roles.json', mode='w') as fichier:
            json.dump(data, fichier, indent=4)

        os.remove(file_path)
        await interaction.response.send_message("Le config_secret_roles.json à bien été remplacé", ephemeral=True)
    
@bot.slash_command(name="insert_temp_channels", description="Remplace le temp_channels.json par celui fourni",guild_ids=[SAVE_GUILD_ID])
@discord.option("message_id", str, description= "Id du message contenant le json")
async def insert_json_secret_command(interaction: discord.Interaction, message_id: str ):
    if interaction.user.id != MY_ID:
        await interaction.response.send_message("Vous ne pouvez pas faire cela", ephemeral=True)
    else:
        guild = bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID)
        message = await channel.fetch_message(message_id)
        attachment = message.attachments[0]
        
        file_path = f"./json/temp_{attachment.filename}"
        await attachment.save(file_path)


        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        file.close()


        with open('./json/temp_channels.json', mode='w') as fichier:
            json.dump(data, fichier, indent=4)

        os.remove(file_path)
        await interaction.response.send_message("Le temp_channels.json à bien été remplacé", ephemeral=True)



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

