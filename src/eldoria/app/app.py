import logging

import discord

from eldoria.app.banner import startup_banner
from eldoria.app.bot import EldoriaBot
from eldoria.app.startup import startup
from eldoria.config import TOKEN

log = logging.getLogger(__name__)



def create_bot() -> EldoriaBot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = EldoriaBot(intents=intents)    
    return bot


def main(started_at: float):
    if not TOKEN:
        raise RuntimeError("discord_token manquant dans le .env")

    print(startup_banner())
    bot = create_bot()
    startup(bot)

    bot._started_at = started_at
    log.info("⏳ Connexion à Discord…")
    bot.run(TOKEN)
