"""Cog de gestion des rôles secrets.

Permet d'attribuer un rôle à un utilisateur lorsqu'il envoie un message spécifique dans un channel spécifique.
Inclut des commandes pour ajouter, supprimer et lister les rôles secrets configurés sur le serveur.
"""

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.roles.autocompletion import message_secret_role_autocomplete
from eldoria.ui.roles.embeds import build_list_secret_roles_embed
from eldoria.utils.guards import (
    require_guild_ctx,
    require_role_assignable_by_bot,
    require_secretrole_exists,
    require_secretrole_not_conflicting,
)


class SecretRoles(commands.Cog):
    """Cog de gestion des rôles secrets.

    Permet d'attribuer un rôle à un utilisateur lorsqu'il envoie un message spécifique dans un channel spécifique.
    Inclut des commandes pour ajouter, supprimer et lister les rôles secrets configurés sur le serveur.
    """
    
    secretrole = SlashCommandGroup(
        name="secretrole",
        description="Gère les rôles secrets (ajouter, supprimer, lister).",
        default_member_permissions=discord.Permissions(manage_roles=True)
    )

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog SecretRoles avec une référence au bot et à son service de gestion des rôles."""
        self.bot = bot
        self.role = self.bot.services.role

    @secretrole.command(name="add", description="Attribue un role défini si l'utilisateur entre le bon message dans le bon channel.")
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @commands.has_permissions(manage_roles=True)
    async def sr_add(self, ctx: discord.ApplicationContext, message: str, channel: discord.TextChannel, role: discord.Role) -> None:
        """Commande slash /secretrole add : attribue un role défini si l'utilisateur entre le bon message dans le bon channel.
        
        Vérifie les permissions du bot, la configuration de la fonctionnalité, et
        ajoute une règle de rôle secret dans la base de données pour le message,
        le channel et le rôle spécifiés.
        """
        await ctx.defer(ephemeral=True)

        guild, _channel = require_guild_ctx(ctx)
        guild_id = guild.id

        bot_member = guild.me
        require_role_assignable_by_bot(bot_member, role)
        
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = self.role.sr_match(guild_id, channel_id, message_str)
        require_secretrole_not_conflicting(message=message_str, existing_role_id=existing_role_id, role_id=role.id)

        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)

        self.role.sr_upsert(guild_id, channel_id, message_str, role.id)
        await ctx.followup.send(content=f"Le rôle <@&{role.id}> est bien associée au message suivant : `{message}` dans le channel {channel.mention}")

    @secretrole.command(name="remove", description="Supprime l'attibution d'un secret_role déjà paramétré.")
    @discord.option("channel", discord.TextChannel, description="Le channel cible pour le message.")
    @discord.option("message", str, description="Le message exact pour que le rôle soit attribué.", autocomplete=message_secret_role_autocomplete)
    @commands.has_permissions(manage_roles=True)
    async def sr_remove(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, message: str)-> None:
        """Commande slash /secretrole remove : supprime l'atibution d'un secret_role déjà paramétré.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, et
        supprime la règle de rôle secret correspondante de la base de données.
        """
        await ctx.defer(ephemeral=True)

        guild, _channel = require_guild_ctx(ctx)
        
        guild_id = guild.id
        channel_id = channel.id
        message_str = str(message)

        existing_role_id = self.role.sr_match(guild_id, channel_id, message_str)
        require_secretrole_exists(message=message_str, existing_role_id=existing_role_id)

        self.role.sr_delete(guild_id, channel_id, message_str)
        await ctx.followup.send(content=f"Le message `{message_str}` n'attribue plus de rôle")

    @secretrole.command(name="list", description="Affiche la liste des tous les rôles attribués avec un message secret.")
    @commands.has_permissions(manage_roles=True)
    async def sr_list(self, ctx: discord.ApplicationContext)-> None:
        """Commande slash /secretrole list : affiche la liste des tous les rôles attribués avec un message secret.
        
        Récupère les rôles secrets du serveur, les organise par channel et message, et affiche le tout dans un embed paginé.
        """
        await ctx.defer(ephemeral=True)
        
        guild, _channel = require_guild_ctx(ctx)
        
        guild_id = guild.id
        secret_roles_guild_list = self.role.sr_list_by_guild_grouped(guild_id)

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
