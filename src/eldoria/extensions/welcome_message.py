"""Cog de gestion des messages de bienvenue, permettant d'envoyer un message personnalisé lorsqu'un nouveau membre rejoint un serveur.

Inclut des commandes pour configurer le salon de bienvenue, activer ou désactiver les messages de bienvenue.
"""

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.welcome.embeds import build_welcome_embed


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
                return

            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                return

            embed, emojis = await build_welcome_embed(guild_id=guild_id, member=member, bot=self.bot)

            message = await channel.send(content=f"||{member.mention}||", embed=embed)

            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except (discord.Forbidden, discord.HTTPException):
                    # manque de perms, emoji invalide, rate limit, etc.
                    continue

        except Exception:
            # On ne casse jamais le bot sur un event
            return



    # -------------------- Commands --------------------
    @commands.slash_command(name="welcome_setup", description="(Admin) Définit le salon des messages d'arrivée et active la fonctionnalité.")
    @discord.option("channel", discord.TextChannel, description="Salon où envoyer les messages de bienvenue")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_setup(self, ctx: discord.ApplicationContext, channel: discord.TextChannel) -> None:
        """Commande slash /welcome_setup : défini le salon des messages d'arrivée et active la fonctionnalité.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité,
        et met à jour la configuration dans la base de données pour définir le salon de bienvenue et activer les messages de bienvenue.
        """
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id

        # channel_id est NOT NULL -> on s'assure que la ligne existe
        self.welcome.ensure_defaults(guild_id)
        self.welcome.set_config(guild_id, channel_id=channel.id, enabled=True)

        await ctx.followup.send(
            content=f"✅ Messages de bienvenue configurés dans {channel.mention} et **activés**.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.slash_command(name="welcome_enable", description="(Admin) Active les messages d'arrivée.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_enable(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /welcome_enable : active les messages de bienvenue pour le serveur.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité,
        et met à jour la configuration dans la base de données pour activer les messages de bienvenue.
        Si aucun salon n'est configuré, invite l'utilisateur à utiliser /welcome_setup.
        """
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        self.welcome.ensure_defaults(guild_id)

        channel_id = self.welcome.get_channel_id(guild_id)
        if not channel_id:
            await ctx.followup.send(
                content=(
                    "⚠️ Aucun salon de bienvenue n'est configuré. "
                    "Utilise `/welcome_setup` pour choisir un salon."
                )
            )
            return

        self.welcome.set_enabled(guild_id, True)
        await ctx.followup.send(content="✅ Messages de bienvenue **activés**.")

    @commands.slash_command(name="welcome_disable", description="(Admin) Désactive les messages d'arrivée.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /welcome_disable : désactive les messages de bienvenue pour le serveur.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité,
        et met à jour la configuration dans la base de données pour désactiver les messages de bienvenue.
        """
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        self.welcome.ensure_defaults(guild_id)
        self.welcome.set_enabled(guild_id, False)
        await ctx.followup.send(content="⛔ Messages de bienvenue **désactivés**.")



def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation de l'extension, appelée par le loader d'extensions du bot."""
    bot.add_cog(WelcomeMessage(bot))
