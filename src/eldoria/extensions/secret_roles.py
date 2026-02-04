import discord
from discord.ext import commands

from eldoria.ui.roles.embeds import build_list_secret_roles_embed

from ..db import database_manager
from ..ui.common import pagination


# -------------------- Fonctions pour l'autocompletion --------------------
async def message_secret_role_autocomplete(interaction: discord.AutocompleteContext):
    user_input = (interaction.value or "").lower()
    guild_id = interaction.interaction.guild.id
    channel_id = interaction.options.get("channel")
    all_messages = database_manager.sr_list_messages(guild_id=guild_id, channel_id=channel_id)
    return [m for m in all_messages if user_input in m.lower()][:25]


class SecretRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="add_secret_role",
        description="Attribue un role défini si l'utilisateur entre le bon message dans le bon channel.",
    )
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_secret_role(self, ctx: discord.ApplicationContext, message: str, channel: discord.TextChannel, role: discord.Role):
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        bot_member = guild.get_member(self.bot.user.id)
        bot_highest_role = max(bot_member.roles, key=lambda r: r.position)
        if role.position >= bot_highest_role.position:
            await ctx.followup.send(content=f"Je ne peux pas attribuer le rôle <@&{role.id}> car il est au-dessus de mes permissions.")
            return

        guild_id = guild.id
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = database_manager.sr_match(guild_id, channel_id, message_str)
        if existing_role_id is not None and existing_role_id != role.id:
            await ctx.followup.send(
                content=f"Le message `{message_str}` est déjà associé au rôle <@&{existing_role_id}> dans le même channel."
            )
            return

        try:
            await bot_member.add_roles(role)
            await bot_member.remove_roles(role)
        except discord.Forbidden:
            await ctx.followup.send(content="Je n'ai pas le droit de gérer ce rôle.")
            return

        database_manager.sr_upsert(guild_id, channel_id, message_str, role.id)
        await ctx.followup.send(content=f"Le rôle <@&{role.id}> est bien associée au message suivant : `{message}`")

    @commands.slash_command(name="delete_secret_role", description="Supprime l'attibution d'un secret_role déjà paramétré.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def delete_secret_role(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, message: str):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = database_manager.sr_match(guild_id, channel_id, message_str)
        if existing_role_id is None:
            await ctx.followup.send(content=f"Aucune attribution trouvée pour le message `{message_str}` dans ce channel.")
            return

        database_manager.sr_delete(guild_id, channel_id, message_str)
        await ctx.followup.send(content=f"Le message `{message_str}` n'attribue plus de rôle")

    @commands.slash_command(name="list_of_secret_roles", description="Affiche la liste des tous les rôles attribués avec un message secret.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def list_of_secret_roles(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        secret_roles_guild_list = database_manager.sr_list_by_guild_grouped(guild_id)

        await ctx.defer(ephemeral=True)
        paginator = pagination.Paginator(
            items=secret_roles_guild_list,
            embed_generator=build_list_secret_roles_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)


def setup(bot: commands.Bot):
    bot.add_cog(SecretRoles(bot))
