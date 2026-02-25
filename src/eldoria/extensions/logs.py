"""Module pour les commandes liées aux logs du bot Eldoria."""
import logging

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.config import LOG_ENABLED, SAVE_GUILD_ID, get_log_admin_id
from eldoria.utils.reader import tail_lines

log = logging.getLogger(__name__)

class Logs(commands.Cog):
    """Cog pour les commandes liées aux logs du bot."""

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog Logs avec une référence au bot."""
        self.bot = bot
        self.est_deconnecte = False

        self.log_enabled: bool = LOG_ENABLED
        if self.log_enabled:
            self.admin_user_id: int = get_log_admin_id()

    def _enabled(self) -> bool:
        return self.log_enabled
    
    # === Listeners ===
    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        """Listener pour l'événement de déconnexion de la gateway Discord, qui log une alerte."""
        if self.est_deconnecte:
            return
        self.est_deconnecte = True
        log.warning("🛑 Déconnexion de la gateway Discord")

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        """Listener pour l'événement de connexion à la gateway Discord, qui log une info avec le nom et l'ID du bot."""
        self.est_deconnecte = False
        log.info("🔌 Connexion à la gateway Discord établie")

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        """Listener pour l'événement de reprise de session (RESUMED) de la gateway Discord, qui log une info."""
        self.est_deconnecte = False
        log.info("🔁 Session Discord reprise avec succès")


    # === Commands ===
    @commands.slash_command(name="logs", description="Envoie la fin du dernier fichier de log du bot dans ce salon.", 
                            guild_ids=[SAVE_GUILD_ID] if SAVE_GUILD_ID else None)
    async def logs_command(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash pour envoyer la fin du dernier fichier de log du bot dans le salon."""
        await ctx.defer(ephemeral=True)
        
        if not self._enabled():
            await ctx.followup.send(content="Feature logs non configurée.")
            return
        
        if ctx.user.id != self.admin_user_id:
            await ctx.followup.send(content="Vous ne pouvez pas faire cela")
            return
        log.info("Utilisation de la commande logs par %s", ctx.user.name)
        
        content = tail_lines()

        # Discord limite ~2000 chars / message
        if len(content) > 1900:
            # renvoyer en fichier texte si trop long
            import io
            data = content.encode("utf-8", errors="replace")
            file = discord.File(fp=io.BytesIO(data), filename="bot.log.tail.txt")
            await ctx.followup.send(file=file, ephemeral=True)
        else:
            await ctx.followup.send(f"```text\n{content}\n```", ephemeral=True)


def setup(bot: EldoriaBot) -> None:
    """Fonction de setup pour ajouter le cog Logs au bot."""
    bot.add_cog(Logs(bot))