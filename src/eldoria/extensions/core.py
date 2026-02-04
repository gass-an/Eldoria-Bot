import discord
from discord.ext import commands

from eldoria.exceptions.general_exceptions import ChannelRequired, GuildRequired, MessageRequired
from eldoria.features.duel.games import init_games
from eldoria.ui.version.embeds import build_version_embed
from eldoria.ui.duels import init_duel_ui


from ..db import database_manager
from ..features import xp_system
from ..ui.help.view import send_help_menu
from ..utils.mentions import level_mention
from ..utils.interactions import reply_ephemeral


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------- Lifecycle --------------------
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.bot.sync_commands()
            print("Les commandes globales ont été synchronisées.")
        except Exception as e:
            print(f"Erreur lors de la synchronisation des commandes : {e}")

        print("Initialisation de la base de données si nécessaire.")
        database_manager.init_db()

        print("Suppression en base des channels temporaires inexistant.")
        for guild in self.bot.guilds:
            rows = database_manager.tv_list_active_all(guild.id)
            for parent_id, channel_id in rows:
                if guild.get_channel(channel_id) is None:
                    database_manager.tv_remove_active(guild.id, parent_id, channel_id)

        print("Initialisation des différents jeux pour les duels.")
        init_games()
        init_duel_ui()

        print(f"{self.bot.user} est en cours d'exécution !\n")

    # -------------------- Messages (router) --------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return

        user_message = message.content or ""

        # ---- XP: on compte aussi les messages avec pièces jointes (même sans texte)
        try:
            if user_message or message.attachments:
                res = await xp_system.handle_message_xp(message)
                if res is not None:
                    new_xp, new_lvl, old_lvl = res
                    if new_lvl > old_lvl:
                        lvl_txt = level_mention(message.guild, new_lvl)
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
            guild_id = message.guild.id
            channel_id = message.channel.id

            role_id = database_manager.sr_match(guild_id, channel_id, str(user_message))
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
    async def help(self, ctx: discord.ApplicationContext):
        await send_help_menu(ctx, self.bot)

    @commands.slash_command(name="ping", description="Ping-pong (pour vérifier que le bot est bien UP !)")
    async def ping_command(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(content="Pong !")

    @commands.slash_command(name="version", description="Affiche la version actuelle du bot")
    async def version(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        embed, files = await build_version_embed()
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)


    # -------------------- Errors --------------------
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error):
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


def setup(bot: commands.Bot):
    bot.add_cog(Core(bot))
