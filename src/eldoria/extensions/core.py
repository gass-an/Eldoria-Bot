import discord
from discord.ext import commands

from ..db import gestionDB
from ..features import xp_system
from ..json_tools import gestionJson
from ..pages import gestionPages
from ..features import embedGenerator
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
        gestionDB.init_db()

        print("Suppression en base des channels temporaires inexistant")
        for guild in self.bot.guilds:
            rows = gestionDB.tv_list_active_all(guild.id)
            for parent_id, channel_id in rows:
                if guild.get_channel(channel_id) is None:
                    gestionDB.tv_remove_active(guild.id, parent_id, channel_id)

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

            role_id = gestionDB.sr_match(guild_id, channel_id, str(user_message))
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
        help_infos = gestionJson.load_help_json()

        cmd_map = {c.name: c for c in self.bot.application_commands}
        member_perms = ctx.user.guild_permissions

        async def is_command_visible(cmd_name: str) -> bool:
            cmd = cmd_map.get(cmd_name)
            if cmd is None:
                return False

            dp = getattr(cmd, "default_member_permissions", None)
            if dp is not None:
                if (member_perms.value & dp.value) != dp.value:
                    return False

            try:
                can = await cmd.can_run(ctx)
                if not can:
                    return False
            except Exception:
                return False

            return True

        filtered = {}
        for name, desc in help_infos.items():
            if await is_command_visible(name):
                filtered[name] = desc

        list_help_info = list(filtered.items())
        if not list_help_info:
            await ctx.respond(
                "Aucune commande disponible avec vos permissions.",
                ephemeral=True,
            )
            return

        await ctx.defer(ephemeral=True)
        paginator = gestionPages.Paginator(
            items=list_help_info,
            embed_generator=embedGenerator.generate_help_embed,
            identifiant_for_embed=None,
            bot=None,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator, ephemeral=True)

    @commands.slash_command(name="ping", description="Ping-pong (pour vérifier que le bot est bien UP !)")
    async def ping_command(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await ctx.followup.send(content="Pong !")

    # -------------------- Errors --------------------
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error):
        err = getattr(error, "original", error)

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
