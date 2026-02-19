"""Cog de gestion des messages de bienvenue, permettant d'envoyer un message personnalisé lorsqu'un nouveau membre rejoint un serveur.

Inclut des commandes pour configurer le salon de bienvenue, activer ou désactiver les messages de bienvenue.
"""

import logging

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.welcome.embeds import build_welcome_embed
from eldoria.ui.welcome.panel import WelcomePanelView
from eldoria.utils.discord_utils import require_guild_ctx

log = logging.getLogger(__name__)

class WelcomeMessage(commands.Cog):
    """Cog de gestion des messages de bienvenue, permettant d'envoyer un message personnalisé lorsqu'un nouveau membre rejoint un serveur.
    
    Inclut des commandes pour configurer le salon de bienvenue, activer ou désactiver les messages de bienvenue.
    """
    
    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog WelcomeMessage avec une référence au bot et à son service de gestion des messages de bienvenue."""
        self.bot = bot
        self.welcome = self.bot.services.welcome

        # -------------------- Listener (optional but useful) --------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Événement déclenché lorsqu'un nouveau membre rejoint un serveur.
        
        Vérifie la configuration des messages de bienvenue pour le serveur, et si activé,
        envoie un message de bienvenue personnalisé dans le salon configuré,
        avec une mention du membre et un embed contenant des informations sur le serveur et des réactions interactives.
        """
        try:
            guild = member.guild
            guild_id = guild.id

            cfg = self.welcome.get_config(guild_id)
            if not cfg.get("enabled"):
                return

            channel_id = int(cfg.get("channel_id") or 0)
            if not channel_id:
                return

            channel = guild.get_channel(channel_id)
            if channel is None:
                log.warning(
                    "Welcome: salon introuvable (guild_id=%s, channel_id=%s)",
                    guild_id,
                    channel_id,
                )
                return

            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                log.warning(
                    "Welcome: salon invalide (guild_id=%s, channel_id=%s, type=%s)",
                    guild_id,
                    channel_id,
                    type(channel).__name__,
                )
                return

            embed, emojis = await build_welcome_embed(guild_id=guild_id, member=member, bot=self.bot)

            message = await channel.send(content=f"||{member.mention}||", embed=embed)

            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except (discord.Forbidden, discord.HTTPException):
                    log.warning(
                        "Welcome: impossible d'ajouter une réaction (guild_id=%s, message_id=%s, emoji=%s)",
                        guild_id,
                        message.id,
                        emoji,
                    )
                    continue

        except Exception:
            log.exception(
                "Welcome: erreur inattendue dans on_member_join (guild_id=%s, user_id=%s)",
                member.guild.id,
                member.id,
            )



    # -------------------- Commands --------------------
    @commands.slash_command(name="welcome", description="(Admin) Configure les messages de bienvenue via un panneau interactif.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_panel(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /welcome : panneau interactif (activer/désactiver + choix salon)."""
        await ctx.defer(ephemeral=True)
        guild, _channel = require_guild_ctx(ctx)

        view = WelcomePanelView(welcome_service=self.welcome, author_id=ctx.author.id, guild=guild)
        embed, files = view.current_embed()
        await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)



def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation de l'extension, appelée par le loader d'extensions du bot."""
    bot.add_cog(WelcomeMessage(bot))
