"""Cog de gestion des sauvegardes de la base de données SQLite.

Permet d'envoyer une copie du fichier .db dans un channel Discord à la demande ou automatiquement à un horaire défini.
Inclut des commandes pour faire une sauvegarde manuelle et pour remplacer la base de données par un fichier .db fourni via un message Discord.
"""
import asyncio
import logging
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from eldoria.app.bot import EldoriaBot
from eldoria.config import (
    AUTO_SAVE_ENABLED,
    AUTO_SAVE_TIME,
    AUTO_SAVE_TZ,
    MY_ID,
    SAVE_CHANNEL_ID,
    SAVE_ENABLED,
    SAVE_GUILD_ID,
)
from eldoria.exceptions.general import InvalidMessageId
from eldoria.utils.db_validation import is_valid_sqlite_db
from eldoria.utils.discord_utils import get_text_or_thread_channel

log = logging.getLogger(__name__)

class Saves(commands.Cog):
    """Cog de gestion des sauvegardes de la base de données SQLite.

    Permet d'envoyer une copie du fichier .db dans un channel Discord à la demande ou automatiquement à un horaire défini.
    Inclut des commandes pour faire une sauvegarde manuelle et pour remplacer la base de données par un fichier .db fourni via un message Discord.
    """

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog Saves avec une référence au bot et à ses services de sauvegarde et de gestion des channels temporaires.
    
        Démarre l'auto-save si la fonctionnalité est configurée.
        """
        self.bot = bot
        self.save = self.bot.services.save
        self.temp_voice = self.bot.services.temp_voice

        self.save_enabled: bool = SAVE_ENABLED
        if self.save_enabled:
            assert MY_ID is not None and SAVE_GUILD_ID is not None and SAVE_CHANNEL_ID is not None
            self.admin_user_id: int = MY_ID
            self.save_guild_id: int = SAVE_GUILD_ID
            self.save_channel_id: int = SAVE_CHANNEL_ID

        if self.save_enabled and AUTO_SAVE_ENABLED:
            self._auto_save_time = self._parse_auto_time(AUTO_SAVE_TIME)
            if self._auto_save_time is not None:
                self.auto_save.start()

    def _enabled(self) -> bool:
        return self.save_enabled

    def _auto_enabled(self) -> bool:
        return AUTO_SAVE_ENABLED

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
            log.warning(
                "Configuration AUTO_SAVE_TIME invalide (%s). "
                "Format attendu : HH:MM (ex: 03:30). "
                "L'auto-save est désactivé.",
                value,
            )
            return None

    async def _send_db_backup(self, *, channel: discord.abc.Messageable, reason: str) -> None:
        """Fait une sauvegarde temporaire et envoie le .db dans le channel."""
        db_path = self.save.get_db_path()

        if not os.path.exists(db_path):
            log.warning("Sauvegarde DB impossible : fichier introuvable (%s)", db_path)
            await channel.send("Fichier DB introuvable !")
            return

        tmp_backup = "./temp_eldoria_backup.db"

        try:
            await asyncio.to_thread(self.save.backup_to_file, tmp_backup)
        except Exception:
            log.exception("Échec lors de la création de la sauvegarde temporaire.")
            return

        filename = f"Eldoria_{datetime.now().strftime('%Y%m%d')}.db"

        try:
            with open(tmp_backup, "rb") as f:
                await channel.send(
                    content=reason,
                    file=discord.File(f, filename=filename),
                )
        except Exception:
            log.exception("Échec lors de l'envoi du fichier de sauvegarde.")
            return
        finally:
            try:
                os.remove(tmp_backup)
            except OSError:
                log.warning("Impossible de supprimer le fichier temporaire (%s)", tmp_backup)

    @tasks.loop(minutes=1)
    async def auto_save(self) -> None:
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
    
        channel = await get_text_or_thread_channel(self.bot, self.save_channel_id)
        
        await self._send_db_backup(
            channel=channel,
            reason="Sauvegarde automatique quotidienne du fichier SQLite.",
        )

        self._last_auto_save_date = now.date()

    @auto_save.before_loop
    async def _wait_until_ready(self) -> None:
        await self.bot.wait_until_ready()

    def cog_unload(self) -> None:
        """Arrête la loop d'auto-save lors du déchargement du cog."""
        try:
            self.auto_save.cancel()
            log.info("Loop d'auto-save arrêtée proprement.")
        except Exception:
            log.exception("Erreur lors de l'arrêt de la loop d'auto-save.")

    @commands.slash_command(name="manual_save", description="Envoie la base SQLite (.db) dans un channel précis", 
                            guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None)
    async def manual_save_command(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /manual_save : envoie une copie du fichier .db dans un channel Discord défini.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, et la présence du fichier .db avant d'envoyer la sauvegarde.
        """
        await ctx.defer(ephemeral=True)

        if not self._enabled():
            await ctx.followup.send(content="Feature save non configurée (.env).")
            return

        if ctx.user.id != self.admin_user_id:
            await ctx.followup.send(content="Vous ne pouvez pas faire cela")
            return

        channel = await get_text_or_thread_channel(self.bot, self.save_channel_id)

        if not os.path.exists(self.save.get_db_path()):
            await channel.send("Fichier DB introuvable !")
            await ctx.followup.send(content="❌ DB introuvable.")
            return

        await self._send_db_backup(
            channel=channel,
            reason="Sauvegarde du fichier SQLite suite à une demande.",
        )

        await ctx.followup.send(content="✅ DB bien envoyée !")


    @commands.slash_command(name="insert_db", description="Remplace la base de données SQLite par celle fournie (message_id dans le channel de save)", 
                            guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None,)
    @discord.option("message_id", str, description="Id du message contenant le fichier .db")
    async def insert_db_command(self, ctx: discord.ApplicationContext, message_id: str) -> None:
        """Commande slash /insert_db : remplace la base de données SQLite par un fichier .db fourni via un message Discord.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, la validité du message et du fichier attaché,
        puis remplace la base de données par le nouveau fichier après vérification qu'il s'agit d'une base de données SQLite valide.
        """
        await ctx.defer(ephemeral=True)

        if not self._enabled():
            await ctx.followup.send(content="Feature save non configurée (.env).")
            return

        if ctx.user.id != self.admin_user_id:
            await ctx.followup.send(content="Vous ne pouvez pas faire cela")
            return

        channel = await get_text_or_thread_channel(self.bot, self.save_channel_id)
        
        if not message_id.isdigit():
            raise InvalidMessageId()
        msg = await channel.fetch_message(int(message_id))

        if not msg.attachments:
            await ctx.followup.send(content="❌ Aucun fichier attaché sur ce message.")
            return

        attachment = msg.attachments[0]

        if not await is_valid_sqlite_db(attachment):
            await ctx.followup.send(content="❌ Le fichier fourni n'est pas une base de données SQLite valide (.db).")
            return

        db_path = Path(self.save.get_db_path())  # convertit en Path
        data_dir = db_path.parent
        data_dir.mkdir(parents=True, exist_ok=True)

        tmp_new = data_dir / f"temp_{attachment.filename}"
        await attachment.save(tmp_new)

        try:
            await asyncio.to_thread(self.save.replace_db_file, str(tmp_new))
            self.save.init_db()
        finally:
            if tmp_new.exists():
                try:
                    tmp_new.unlink()
                except OSError:
                    log.warning("Impossible de supprimer le fichier temporaire %s", tmp_new)

        # Suppression en base des channels temporaires inexistant
        for guild in self.bot.guilds:
                    rows = self.temp_voice.list_active_all(guild.id)
                    for parent_id, channel_id in rows:
                        if guild.get_channel(channel_id) is None:
                            self.temp_voice.remove_active(guild.id, parent_id, channel_id)
        
        await ctx.followup.send(content="✅ Base de données remplacée avec succès.")


def setup(bot: EldoriaBot) -> None:
    """Fonction de setup pour ajouter le cog Saves au bot."""
    bot.add_cog(Saves(bot))
