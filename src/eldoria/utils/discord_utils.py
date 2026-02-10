import discord
import re

from eldoria.exceptions.general_exceptions import ChannelRequired, GuildRequired, UserRequired

def extract_id_from_link(link: str):
    ids_match = re.match(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)", link)
    if ids_match:
        guild_id = int(ids_match.group(1))
        channel_id = int(ids_match.group(2))
        message_id = int(ids_match.group(3))
        return guild_id, channel_id, message_id
    return None, None, None

async def find_channel_id(bot: discord.Client, message_id: int, guild_id: int) -> int | None:
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
    return None

async def get_member_by_id_or_raise(guild: discord.Guild, member_id: int) -> discord.Member:
    member = guild.get_member(member_id)
    if member is not None:
        return member
    
    try:
        return await guild.fetch_member(member_id)
    except discord.NotFound:
        raise ValueError(f"Member {member_id} not found in guild {guild.id}")


async def get_text_or_thread_channel(bot: discord.Client, channel_id: int) -> discord.abc.Messageable:
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)

    if not isinstance(
        channel,
        (discord.TextChannel, discord.Thread, discord.DMChannel),
    ):
        raise ChannelRequired("Channel is not messageable")

    return channel

def require_guild(interaction: discord.Interaction) -> discord.Guild:
    if interaction.guild is None:
        raise GuildRequired()
    return interaction.guild

def require_user(interaction: discord.Interaction) -> discord.User | discord.Member:
    if interaction.user is None:
        raise UserRequired()
    return interaction.user

def require_user_id(interaction: discord.Interaction) -> int:
    if interaction.user is None:
        raise UserRequired()
    return interaction.user.id