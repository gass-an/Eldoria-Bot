import asyncio
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from discord.ext import tasks

from ..config import AUTO_SAVE_TIME, AUTO_SAVE_TZ, MY_ID, SAVE_GUILD_ID, SAVE_CHANNEL_ID
from ..db import gestionDB
from ..utils.db_validation import is_valid_sqlite_db


class Saves(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Démarre l'auto-save si configuré
        if self._enabled() and self._auto_enabled():
            self._auto_save_time = self._parse_auto_time(AUTO_SAVE_TIME)
            if self._auto_save_time is not None:
                self.auto_save.start()

    def _enabled(self) -> bool:
        return MY_ID is not None and SAVE_GUILD_ID is not None and SAVE_CHANNEL_ID is not None

    def _auto_enabled(self) -> bool:
        return AUTO_SAVE_TIME is not None and AUTO_SAVE_TIME.strip() != ""

    def _parse_auto_time(self, value: str | None) -> time | None:
        """Parse un horaire HH:MM et retourne un datetime.time avec tzinfo."""
        if not value:
            return None
        try:
            hh, mm = value.strip().split(":", 1)
            hour = int(hh)
            minute = int(mm)
            tz = ZoneInfo(AUTO_SAVE_TZ)
            return time(hour=hour, minute=minute, tzinfo=tz)
        except Exception:
            # En cas de config invalide, on désactive l'auto-save sans casser le bot.
            return None

    async def _send_db_backup(self, *, channel: discord.abc.Messageable, reason: str):
        """Fait une sauvegarde temporaire et envoie le .db dans le channel."""
        if not os.path.exists(gestionDB.DB_PATH):
            await channel.send("Fichier DB introuvable !")
            return

        tmp_backup = "./temp_eldoria_backup.db"
        await asyncio.to_thread(gestionDB.backup_to_file, tmp_backup)

        filename = f"Eldoria_{datetime.now().strftime('%Y%m%d')}.db"
        with open(tmp_backup, "rb") as f:
            await channel.send(
                content=reason,
                file=discord.File(f, filename=filename),
            )

        try:
            os.remove(tmp_backup)
        except OSError:
            pass

    @tasks.loop(minutes=1)
    async def auto_save(self):
        """Envoie automatiquement la DB une fois par jour à l'heure configurée."""
        if not self._enabled() or not self._auto_enabled():
            return

        # Si on n'a pas réussi à parser l'heure, on ne fait rien.
        configured_time = getattr(self, "_auto_save_time", None)
        if configured_time is None:
            return

        now = datetime.now(tz=configured_time.tzinfo)
        if now.hour != configured_time.hour or now.minute != configured_time.minute:
            return

        # Évite les doublons (ex: redémarrage du bot, ou boucle qui repasse plusieurs fois dans la même minute)
        last_date = getattr(self, "_last_auto_save_date", None)
        if last_date == now.date():
            return

        guild = self.bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID) if guild else None
        if channel is None:
            return

        await self._send_db_backup(
            channel=channel,
            reason="Sauvegarde automatique quotidienne du fichier SQLite.",
        )

        self._last_auto_save_date = now.date()

    @auto_save.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()

    @commands.slash_command(name="manual_save", description="Envoie la base SQLite (.db) dans un channel précis", 
                            guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None)
    async def manual_save_command(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if not self._enabled():
            await ctx.followup.send(content="Feature save non configurée (.env).")
            return

        if ctx.user.id != MY_ID:
            await ctx.followup.send(content="Vous ne pouvez pas faire cela")
            return

        guild = self.bot.get_guild(SAVE_GUILD_ID)
        channel = guild.get_channel(SAVE_CHANNEL_ID) if guild else None
        if channel is None:
            await ctx.followup.send(content="❌ Channel de save introuvable.")
            return

        if not os.path.exists(gestionDB.DB_PATH):
            await channel.send("Fichier DB introuvable !")
            await ctx.followup.send(content="❌ DB introuvable.")
            return

        await self._send_db_backup(
            channel=channel,
            reason="Sauvegarde du fichier SQLite suite à une demande.",
        )

        await ctx.followup.send(content="✅ DB bien envoyée !")

    def cog_unload(self):
        try:
            self.auto_save.cancel()
        except Exception:
            pass

    @commands.slash_command(name="insert_db", description="Remplace la base de données SQLite par celle fournie (message_id dans le channel de save)", 
                            guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None,)
    @discord.option("message_id", str, description="Id du message contenant le fichier .db")
    async def insert_db_command(self, ctx: discord.ApplicationContext, message_id: str):
        await ctx.defer(ephemeral=True)

        if not self._enabled():
            await ctx.followup.send(content="Feature save non configurée (.env).")
            return

        if ctx.user.id != MY_ID:
            await ctx.followup.send(content="Vous ne pouvez pas faire cela")
            return

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
