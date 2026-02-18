"""Cog de gestion des rôles secrets.

Permet d'attribuer un rôle à un utilisateur lorsqu'il envoie un message spécifique dans un channel spécifique.
Inclut des commandes pour ajouter, supprimer et lister les rôles secrets configurés sur le serveur.
"""

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.roles.autocompletion import message_secret_role_autocomplete
from eldoria.ui.roles.embeds import build_list_secret_roles_embed


class SecretRoles(commands.Cog):
    """Cog de gestion des rôles secrets.

    Permet d'attribuer un rôle à un utilisateur lorsqu'il envoie un message spécifique dans un channel spécifique.
    Inclut des commandes pour ajouter, supprimer et lister les rôles secrets configurés sur le serveur.
    """

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog SecretRoles avec une référence au bot et à son service de gestion des rôles."""
        self.bot = bot
        self.role = self.bot.services.role

    @commands.slash_command(
        name="add_secret_role",
        description="Attribue un role défini si l'utilisateur entre le bon message dans le bon channel.",
    )
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_secret_role(self, ctx: discord.ApplicationContext, message: str, channel: discord.TextChannel, role: discord.Role) -> None:
        """Commande slash /add_secret_role : attribue un role défini si l'utilisateur entre le bon message dans le bon channel.
        
        Vérifie les permissions du bot, la configuration de la fonctionnalité, et
        ajoute une règle de rôle secret dans la base de données pour le message,
        le channel et le rôle spécifiés.
        """
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        bot_member = guild.me
        if bot_member is None:
            await ctx.followup.send(content="Je ne suis pas correctement initialisé sur ce serveur.")
            return
        
        bot_highest_role = max(bot_member.roles, key=lambda r: r.position)
        if role.position >= bot_highest_role.position:
            await ctx.followup.send(content=f"Je ne peux pas attribuer le rôle <@&{role.id}> car il est au-dessus de mes permissions.")
            return

        guild_id = guild.id
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = self.role.sr_match(guild_id, channel_id, message_str)
        if existing_role_id is not None and existing_role_id != role.id:
            await ctx.followup.send(
                content=f"Le message `{message_str}` est déjà associé au rôle <@&{existing_role_id}> dans le même channel."
            )
            return

        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)

        self.role.sr_upsert(guild_id, channel_id, message_str, role.id)
        await ctx.followup.send(content=f"Le rôle <@&{role.id}> est bien associée au message suivant : `{message}`")

    @commands.slash_command(name="delete_secret_role", description="Supprime l'attibution d'un secret_role déjà paramétré.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def delete_secret_role(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, message: str)-> None:
        """Commande slash /delete_secret_role : supprime l'atibution d'un secret_role déjà paramétré.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, et
        supprime la règle de rôle secret correspondante de la base de données.
        """
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = self.role.sr_match(guild_id, channel_id, message_str)
        if existing_role_id is None:
            await ctx.followup.send(content=f"Aucune attribution trouvée pour le message `{message_str}` dans ce channel.")
            return

        self.role.sr_delete(guild_id, channel_id, message_str)
        await ctx.followup.send(content=f"Le message `{message_str}` n'attribue plus de rôle")

    @commands.slash_command(name="list_of_secret_roles", description="Affiche la liste des tous les rôles attribués avec un message secret.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def list_of_secret_roles(self, ctx: discord.ApplicationContext)-> None:
        """Commande slash /list_of_secret_roles : affiche la liste des tous les rôles attribués avec un message secret.
        
        Récupère les rôles secrets du serveur, les organise par channel et message, et affiche le tout dans un embed paginé.
        """
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        secret_roles_guild_list = self.role.sr_list_by_guild_grouped(guild_id)

        await ctx.defer(ephemeral=True)
        paginator = Paginator(
            items=secret_roles_guild_list,
            embed_generator=build_list_secret_roles_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)


def setup(bot: EldoriaBot)-> None:
    """Fonction de setup pour ajouter le cog SecretRoles au bot."""
    bot.add_cog(SecretRoles(bot))
