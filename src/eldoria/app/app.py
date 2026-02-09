import logging
import discord
from discord.ext import commands

from eldoria.app.startup import load_extensions, step

from ..config import TOKEN
from .banner import startup_banner

log = logging.getLogger(__name__)


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(intents=intents)
    step("Initialisation des extensions", lambda: load_extensions(bot), logger=log)
    
    return bot


def main(started_at: float):
    if not TOKEN:
        raise RuntimeError("discord_token manquant dans le .env")

    print(startup_banner())
    bot = create_bot()
    setattr(bot, "_started_at", started_at)
    log.info("⏳ Connexion à Discord…")
    bot.run(TOKEN)
