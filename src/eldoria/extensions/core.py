"""Cog de base pour le bot Eldoria.
    
Gère les événements fondamentaux tels que la connexion, les messages, les commandes de base (help, ping, version) et les erreurs d'application.
"""

import logging
import time

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.general_exceptions import ChannelRequired, GuildRequired, MessageRequired
from eldoria.ui.help.view import send_help_menu
from eldoria.ui.version.embeds import build_version_embed
from eldoria.utils.interactions import reply_ephemeral
from eldoria.utils.mentions import level_mention

log = logging.getLogger(__name__)

class Core(commands.Cog):
    """Cog de base pour le bot Eldoria.
    
    Gère les événements fondamentaux tels que la connexion, les messages, les commandes de base (help, ping, version) et les erreurs d'application.
    """

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog Core avec une référence au bot et à ses services XP et rôle."""
        self.bot = bot
        self.xp = self.bot.services.xp
        self.role = self.bot.services.role

    # -------------------- Lifecycle --------------------
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Événement déclenché lorsque le bot est prêt et connecté à Discord. Synchronise les commandes et affiche les temps de chargement."""
        if getattr(self.bot, "_booted", False):
            return
        self.bot._booted = True

        try:
            await self.bot.sync_commands()
        except Exception:
            log.exception("Erreur lors de la synchronisation des commandes")
        started_at = getattr(self.bot, "_started_at", time.perf_counter())
        discord_started_at = getattr(self.bot, "_discord_started_at", time.perf_counter())
        
        discord_time = (time.perf_counter() - discord_started_at) * 1000
        log.info("✅ %-53s %8.1f ms", "Préparation Discord", discord_time)

        total_time = (time.perf_counter() - started_at)
        log.info("🤖 Bot opérationnel en %.2fs - Connecté en tant que %s (%d guilds)", total_time, self.bot.user, len(self.bot.guilds))

    # -------------------- Messages (router) --------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Événement déclenché à la réception d'un message.
        
        Gère l'attribution de XP pour les messages, les rôles secrets basés sur le contenu des messages,
        et traite les commandes préfixées si nécessaire.
        """
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return

        user_message = message.content or ""
        guild_id = message.guild.id
        # ---- XP: on compte aussi les messages avec pièces jointes (même sans texte)
        try:
            if user_message or message.attachments:
                res = await self.xp.handle_message_xp(message)
                if res is not None:
                    new_xp, new_lvl, old_lvl = res
                    if new_lvl > old_lvl:
                        role_ids = self.xp.get_role_ids(guild_id)
                        lvl_txt = level_mention(message.guild, new_lvl, role_ids)
                        await message.reply(
                            f"🎉 Félicitations {message.author.mention}, tu passes {lvl_txt} !",
                            allowed_mentions=discord.AllowedMentions(
                                users=True,
                                roles=False,  # n'alerte pas tous les membres du rôle
                                replied_user=True,
                            ),
                        )
        except Exception as e:
            print(f"[XP] Erreur handle message: {e}")

        # ---- Secret roles (message exact dans un salon)
        try:
            channel_id = message.channel.id

            role_id = self.role.sr_match(guild_id, channel_id, str(user_message))
            if role_id is not None:
                # On supprime le message pour garder le "secret"
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass

                role = message.guild.get_role(role_id)
                if role:
                    try:
                        await message.author.add_roles(role)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
        except Exception as e:
            print(f"[SecretRole] Erreur: {e}")

        # Important si tu as encore des commandes préfixées (sinon harmless)
        await self.bot.process_commands(message)

    # -------------------- Basic commands --------------------
    @commands.slash_command(name="help", description="Affiche la liste des commandes disponible avec le bot")
    async def help(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /help : affiche la liste des commandes disponible avec le bot, organisée par catégorie et avec des descriptions pour chaque commande."""
        await send_help_menu(ctx, self.bot)

    @commands.slash_command(name="ping", description="Ping-pong (pour vérifier que le bot est bien UP !)")
    async def ping_command(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /ping : répond "Pong" avec la latence du bot en millisecondes, pour vérifier que le bot est bien opérationnel et mesurer sa réactivité."""
        await ctx.defer(ephemeral=True)
        ws_latency = round(self.bot.latency * 1000)
        await ctx.followup.send(content=f"Pong 🏓\nLatence : `{ws_latency} ms`")

    @commands.slash_command(name="version", description="Affiche la version actuelle du bot")
    async def version(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /version : affiche la version actuelle du bot, ainsi que des informations supplémentaires telles que les changements récents ou les liens utiles."""
        await ctx.defer(ephemeral=True)
        embed, files = await build_version_embed()
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)


    # -------------------- Errors --------------------
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Événement déclenché lorsqu'une erreur se produit lors de l'exécution d'une commande slash.
        
        Gère les erreurs courantes telles que les permissions manquantes, les rôles requis, les vérifications échouées,
        et fournit des messages d'erreur clairs et adaptés à l'utilisateur.
        """
        err = getattr(error, "original", error)

        if isinstance(err, GuildRequired):
            await reply_ephemeral(interaction,"❌ Cette commande doit être utilisée sur un serveur.")
            return
        
        if isinstance(err, ChannelRequired):
            await reply_ephemeral(interaction, "❌ Impossible de retrouver le salon associé à cette action.")
            return

        if isinstance(err, MessageRequired):
            await reply_ephemeral(interaction, "❌ Le message associé à cette action est introuvable.")
            return

        if isinstance(err, commands.MissingPermissions):
            missing = ", ".join(err.missing_permissions)
            await reply_ephemeral(interaction, f"❌ Permissions manquantes : **{missing}**.")
            return

        if isinstance(err, commands.BotMissingPermissions):
            missing = ", ".join(err.missing_permissions)
            await reply_ephemeral(interaction, f"❌ Il me manque des permissions : **{missing}**.")
            return

        if isinstance(err, commands.MissingRole):
            await reply_ephemeral(interaction, "❌ Vous n'avez pas le rôle requis pour utiliser cette commande.")
            return

        if isinstance(err, commands.MissingAnyRole):
            await reply_ephemeral(interaction, "❌ Vous n'avez aucun des rôles requis pour utiliser cette commande.")
            return

        if isinstance(err, commands.CheckFailure):
            await reply_ephemeral(interaction, "❌ Vous ne pouvez pas utiliser cette commande.")
            return

        print(f"[CommandError] {type(err).__name__}: {err}")
        await reply_ephemeral(interaction, "❌ Une erreur est survenue lors de l'exécution de la commande.")


def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog Core, appelée lors du chargement de l'extension."""
    bot.add_cog(Core(bot))
