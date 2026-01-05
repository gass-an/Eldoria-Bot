import re, discord
from discord.ext import commands

def extract_id_from_link(link: str):
    ids_match = re.match(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)", link)
    if ids_match:
        guild_id = int(ids_match.group(1))
        channel_id = int(ids_match.group(2))
        message_id = int(ids_match.group(3))
        return guild_id, channel_id, message_id
    return None, None, None

async def find_channel_id(bot: commands.Bot, message_id: int, guild_id: int):
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