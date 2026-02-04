import logging
import discord
from discord.ext import commands

from ..config import TOKEN
from .banner import startup_banner

log = logging.getLogger("eldoria.app")


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(intents=intents)

    log.info("Chargement des extensions")
    for ext in (
        "eldoria.extensions.core",
        "eldoria.extensions.xp",
        "eldoria.extensions.xp_voice",
        "eldoria.extensions.duels",
        "eldoria.extensions.reaction_roles",
        "eldoria.extensions.secret_roles",
        "eldoria.extensions.temp_voice",
        "eldoria.extensions.saves",
        "eldoria.extensions.welcome_message",
    ):
        bot.load_extension(ext)

    return bot


def main():
    if not TOKEN:
        raise RuntimeError("discord_token manquant dans le .env")

    print(startup_banner())
    bot = create_bot()
    bot.run(TOKEN)
