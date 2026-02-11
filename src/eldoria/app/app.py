"""Module principal de l'application EldoriaBot."""

import logging

import discord

from eldoria.app.banner import startup_banner
from eldoria.app.bot import EldoriaBot
from eldoria.app.startup import startup
from eldoria.config import TOKEN

log = logging.getLogger(__name__)



def create_bot() -> EldoriaBot:
    """Crée et retourne une instance du bot Discord avec les intentions nécessaires."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = EldoriaBot(intents=intents)    
    return bot


def main(started_at: float) -> None:
    """Démarre le bot Discord avec le token d'authentification."""
    if not TOKEN:
        raise RuntimeError("discord_token manquant dans le .env")

    print(startup_banner())
    bot = create_bot()
    startup(bot)

    bot.set_started_at(started_at)
    log.info("⏳ Connexion à Discord…")
    bot.run(TOKEN)
