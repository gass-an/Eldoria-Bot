import discord
from discord.ext import commands

from .config import TOKEN


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True  # NOQA
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(intents=intents)

    # Extensions (features)
    print("Chargement des extensions.")
    bot.load_extension("eldoria.extensions.core")
    bot.load_extension("eldoria.extensions.xp")
    bot.load_extension("eldoria.extensions.reaction_roles")
    bot.load_extension("eldoria.extensions.secret_roles")
    bot.load_extension("eldoria.extensions.temp_voice")
    bot.load_extension("eldoria.extensions.saves")
    bot.load_extension("eldoria.extensions.welcome_message")

    return bot


def main():
    if not TOKEN:
        raise RuntimeError("discord_token manquant dans le .env")

    bot = create_bot()
    bot.run(TOKEN)
