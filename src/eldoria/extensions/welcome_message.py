import discord
from discord.ext import commands

from ..db import gestionDB
from ..json_tools.welcomeJson import getWelcomeMessage


class WelcomeMessage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # -------------------- Listener (optional but useful) --------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            guild = member.guild
            guild_id = guild.id

            cfg = gestionDB.wm_get_config(guild_id)
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

            msg = getWelcomeMessage(
                guild_id,
                user=member.mention,
                server=guild.name,
                recent_limit=10,
            )

            await channel.send(msg, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
        except Exception:
            # On ne casse jamais le bot sur un event
            return



    # -------------------- Commands --------------------
    @commands.slash_command(name="welcome_setup", description="(Admin) Définit le salon des messages d'arrivée et active la fonctionnalité.")
    @discord.option("channel", discord.TextChannel, description="Salon où envoyer les messages de bienvenue")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_setup(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id

        # channel_id est NOT NULL -> on s'assure que la ligne existe
        gestionDB.wm_ensure_defaults(guild_id)
        gestionDB.wm_set_config(guild_id, channel_id=channel.id, enabled=True)

        await ctx.followup.send(
            content=f"✅ Messages de bienvenue configurés dans {channel.mention} et **activés**.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.slash_command(name="welcome_enable", description="(Admin) Active les messages d'arrivée.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_enable(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        gestionDB.wm_ensure_defaults(guild_id)

        channel_id = gestionDB.wm_get_channel_id(guild_id)
        if not channel_id:
            await ctx.followup.send(
                content=(
                    "⚠️ Aucun salon de bienvenue n'est configuré. "
                    "Utilise `/welcome_setup` pour choisir un salon."
                )
            )
            return

        gestionDB.wm_set_enabled(guild_id, True)
        await ctx.followup.send(content="✅ Messages de bienvenue **activés**.")

    @commands.slash_command(name="welcome_disable", description="(Admin) Désactive les messages d'arrivée.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        gestionDB.wm_ensure_defaults(guild_id)
        gestionDB.wm_set_enabled(guild_id, False)
        await ctx.followup.send(content="⛔ Messages de bienvenue **désactivés**.")



def setup(bot: commands.Bot):
    bot.add_cog(WelcomeMessage(bot))
