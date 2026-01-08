import asyncio
import os
from datetime import datetime

import discord
from discord.ext import commands

from ..config import MY_ID, SAVE_GUILD_ID, SAVE_CHANNEL_ID
from ..db import gestionDB
from ..utils.db_validation import is_valid_sqlite_db


class Saves(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _enabled(self) -> bool:
        return MY_ID is not None and SAVE_GUILD_ID is not None and SAVE_CHANNEL_ID is not None

    @commands.slash_command(
        name="manual_save",
        description="Envoie la base SQLite (.db) dans un channel précis",
        guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None,
    )
    async def manual_save_command(self, ctx: discord.ApplicationContext):
        if not self._enabled():
            await ctx.respond("Feature save non configurée (.env).", ephemeral=True)
            return

        if ctx.user.id != MY_ID:
            await ctx.respond("Vous ne pouvez pas faire cela", ephemeral=True)
            return

        await ctx.respond("Sauvegarde en cours...", ephemeral=True)

        guild = self.bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID) if guild else None
        if channel is None:
            await ctx.followup.send(content="❌ Channel de save introuvable.")
            return

        if not os.path.exists(gestionDB.DB_PATH):
            await channel.send("Fichier DB introuvable !")
            await ctx.followup.send(content="❌ DB introuvable.")
            return

        tmp_backup = "./temp_eldoria_backup.db"
        await asyncio.to_thread(gestionDB.backup_to_file, tmp_backup)

        filename = f"Eldoria_{datetime.now().strftime('%Y%m%d')}.db"
        with open(tmp_backup, "rb") as f:
            await channel.send(
                content="Sauvegarde du fichier SQLite suite à une demande.",
                file=discord.File(f, filename=filename),
            )

        try:
            os.remove(tmp_backup)
        except OSError:
            pass

        await ctx.followup.send(content="✅ DB bien envoyée !")

    @commands.slash_command(
        name="insert_db",
        description="Remplace la base de données SQLite par celle fournie (message_id dans le channel de save)",
        guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None,
    )
    @discord.option("message_id", str, description="Id du message contenant le fichier .db")
    async def insert_db_command(self, ctx: discord.ApplicationContext, message_id: str):
        if not self._enabled():
            await ctx.respond("Feature save non configurée (.env).", ephemeral=True)
            return

        if ctx.user.id != MY_ID:
            await ctx.respond("Vous ne pouvez pas faire cela", ephemeral=True)
            return

        await ctx.respond("Restauration en cours...", ephemeral=True)

        guild = self.bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID) if guild else None
        if channel is None:
            await ctx.followup.send(content="❌ Channel de save introuvable.")
            return

        try:
            msg = await channel.fetch_message(int(message_id))
        except Exception:
            await ctx.followup.send(content="❌ Message introuvable (vérifie l'ID).")
            return

        if not msg.attachments:
            await ctx.followup.send(content="❌ Aucun fichier attaché sur ce message.")
            return

        attachment = msg.attachments[0]

        if not await is_valid_sqlite_db(attachment):
            await ctx.followup.send(content="❌ Le fichier fourni n'est pas une base de données SQLite valide (.db).")
            return

        tmp_new = f"./temp_{attachment.filename}"
        await attachment.save(tmp_new)

        try:
            await asyncio.to_thread(gestionDB.replace_db_file, tmp_new)
            gestionDB.init_db()
        except Exception as e:
            try:
                if os.path.exists(tmp_new):
                    os.remove(tmp_new)
            except OSError:
                pass
            await ctx.followup.send(content=f"❌ Erreur pendant la restauration : {e}")
            return

        await ctx.followup.send(content="✅ Base de données remplacée avec succès.")


def setup(bot: commands.Bot):
    bot.add_cog(Saves(bot))
