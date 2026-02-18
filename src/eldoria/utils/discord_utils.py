"""Utilitaires pour les interactions avec Discord, comme l'extraction d'IDs à partir de liens, la recherche de canaux, et la validation de contexte d'interaction."""

import re

import discord

from eldoria.exceptions.general import ChannelRequired, GuildRequired, MemberNotFound, UserRequired


def extract_id_from_link(link: str) -> tuple[int | None, int | None, int | None]:
    """Extrait les IDs de serveur, canal et message d'un lien Discord, ou retourne (None, None, None) si le format est invalide."""
    ids_match = re.match(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)", link)
    if ids_match:
        guild_id = int(ids_match.group(1))
        channel_id = int(ids_match.group(2))
        message_id = int(ids_match.group(3))
        return guild_id, channel_id, message_id
    return None, None, None

async def find_channel_id(bot: discord.Client, message_id: int, guild_id: int) -> int | None:
    """Parcourt les canaux textuels d'un serveur pour trouver celui contenant un message donné, et retourne son ID, ou None si non trouvé."""
    guild = bot.get_guild(guild_id)
        
    if not guild:
        return None
    
    for channel in guild.text_channels:
        try:
            await channel.fetch_message(message_id)
            return channel.id
        except discord.NotFound:
            continue
        except discord.Forbidden:
            continue
        except discord.HTTPException:
            continue
    return None

async def get_member_by_id_or_raise(guild: discord.Guild, member_id: int) -> discord.Member:
    """Récupère un membre d'un serveur par son ID, en essayant d'abord le cache puis en fetchant depuis l'API, et lève une exception si le membre n'est pas trouvé."""
    member = guild.get_member(member_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(member_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
        raise MemberNotFound(guild.id, member_id) from e

def require_member(user: discord.User | discord.Member) -> discord.Member:
    """Garantit qu'un utilisateur est un Member (contexte serveur), sinon lève une exception."""
    if not isinstance(user, discord.Member):
        raise UserRequired()
    return user

async def get_text_or_thread_channel(bot: discord.Client, channel_id: int) -> discord.TextChannel | discord.Thread | discord.DMChannel:
    """Récupère un canal textuel ou un thread par son ID, en essayant d'abord le cache puis en fetchant depuis l'API.
    
    Lève une exception si le canal n'est pas trouvé ou n'est pas du bon type.
    """
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            raise ChannelRequired()

    if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
        raise ChannelRequired()

    return channel

def require_guild_ctx(ctx: discord.ApplicationContext) -> tuple[discord.Guild, discord.abc.GuildChannel]:
    """Garantit que la commande est exécutée dans une guild et un channel valide."""
    if ctx.guild is None:
        raise GuildRequired()

    if ctx.channel is None or not isinstance(ctx.channel, discord.abc.GuildChannel):
        raise ChannelRequired()

    return ctx.guild, ctx.channel


def require_guild(interaction: discord.Interaction) -> discord.Guild:
    """Extrait le serveur d'une interaction, ou lève une exception si elle n'est pas dans un contexte de serveur."""
    if interaction.guild is None:
        raise GuildRequired()
    return interaction.guild

def require_user(interaction: discord.Interaction) -> discord.User | discord.Member:
    """Extrait l'utilisateur d'une interaction, ou lève une exception si elle n'est pas dans un contexte de message ou d'interaction utilisateur."""
    if interaction.user is None:
        raise UserRequired()
    return interaction.user

def require_user_id(interaction: discord.Interaction) -> int:
    """Extrait l'identifiant de l'utilisateur d'une interaction, ou lève une exception si elle n'est pas dans un contexte de message ou d'interaction utilisateur."""
    if interaction.user is None:
        raise UserRequired()
    return interaction.user.id