"""Cog de gestion des rôles par réaction, permettant d'associer des réactions à des rôles sur des messages spécifiques.
    
Gère les événements de réaction pour attribuer ou retirer les rôles correspondants, et inclut des commandes pour ajouter,
supprimer et lister les associations de réactions et de rôles.
"""
import logging

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.roles.embeds import build_list_roles_embed
from eldoria.utils.discord_utils import extract_id_from_link, get_text_or_thread_channel
from eldoria.utils.guards import (
    require_guild_ctx,
    require_no_rr_conflict,
    require_role_assignable_by_bot,
    require_specific_guild,
)

log = logging.getLogger(__name__)

class ReactionRoles(commands.Cog):
    """Cog de gestion des rôles par réaction, permettant d'associer des réactions à des rôles sur des messages spécifiques.
    
    Gère les événements de réaction pour attribuer ou retirer les rôles correspondants, et inclut des commandes pour ajouter,
    supprimer et lister les associations de réactions et de rôles.
    """

    reactionrole = SlashCommandGroup(
        name="reactionrole",
        description="Gère les rôles par réaction (ajouter, retirer, lister).",
        default_member_permissions=discord.Permissions(manage_roles=True, manage_messages=True)
    )
    
    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog ReactionRoles avec une référence au bot et à son service de rôle."""
        self.bot = bot
        self.role = self.bot.services.role

    # -------------------- Events --------------------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Gère l'événement de réaction ajoutée.
        
        Vérifie si la réaction correspond à une règle de rôle par réaction, et si oui, attribue le rôle correspondant à l'utilisateur qui a réagi.
        """
        guild_id = payload.guild_id
        if guild_id is None:
            return
        
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None or member == self.bot.user:
            return

        emoji_name = payload.emoji.name
        if emoji_name is None:
            return
        
        role_id = self.role.rr_get_role_id(guild_id, payload.message_id, emoji_name)
        if role_id is None:
            return

        role = guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                log.warning("ReactionRole: Forbidden add_roles (guild=%s user=%s role=%s)", guild_id, payload.user_id, role_id)
            except discord.HTTPException:
                log.warning("ReactionRole: HTTPException add_roles (guild=%s user=%s role=%s)", guild_id, payload.user_id, role_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Gère l'événement de réaction retirée.
        
        Vérifie si la réaction correspond à une règle de rôle par réaction, et si oui,
        retire le rôle correspondant à l'utilisateur qui a retiré sa réaction.
        """
        guild_id = payload.guild_id
        if guild_id is None:
            return

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        emoji_name = payload.emoji.name
        if emoji_name is None:
            return

        role_id = self.role.rr_get_role_id(guild_id, payload.message_id, emoji_name)
        if role_id is None:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role is None or member is None:
            return

        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            log.warning("ReactionRole: Forbidden remove_roles (guild=%s user=%s role=%s)", guild_id, payload.user_id, role_id)
        except discord.HTTPException:
            log.warning("ReactionRole: HTTPException remove_roles (guild=%s user=%s role=%s)", guild_id, payload.user_id, role_id)

    # -------------------- Commands --------------------
    @reactionrole.command(name="add", description="Associe une réaction à un rôle sur un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.option("emoji", str, description="L'émoji de la réaction.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx: discord.ApplicationContext, message_link: str, emoji: str, role: discord.Role) -> None:
        """Commande slash /reactionrole add : associe une réaction sur un message défini à un rôle.
        
        Vérifie les permissions du bot, les conflits d'association existants, ajoute la réaction au message,
        et enregistre la règle de rôle par réaction dans la base de données.
        """
        await ctx.defer(ephemeral=True)

        guild, _channel = require_guild_ctx(ctx)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        require_specific_guild(guild_id, guild.id)

        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        bot_member = guild.me
        require_role_assignable_by_bot(bot_member, role)

        existing = self.role.rr_list_by_message(guild_id, message_id)  # dict: {emoji: role_id}
        require_no_rr_conflict(message_id=message_id, emoji=emoji, role_id=role.id, existing=existing)

        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
        await message.add_reaction(emoji)

        self.role.rr_upsert(guild_id, message_id, emoji, role.id)

        await ctx.followup.send(
            content=f"La réaction {emoji} est bien associée au rôle <@&{role.id}> sur le message sélectionné !\n**Message :** {message_link}"
        )


    @reactionrole.command(name="remove", description="Retire une réaction spécifique d'un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.option("emoji", str, description="L'émoji de la réaction.")
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def rr_remove(self, ctx: discord.ApplicationContext, message_link: str, emoji: str) -> None:
        """Commande slash /reactionrole remove : retire une réaction spécifique d'un message.
        
        Vérifie les permissions du bot, supprime la réaction du message,
        et supprime la règle de rôle par réaction correspondante de la base de données.
        """
        await ctx.defer(ephemeral=True)
        guild, _channel = require_guild_ctx(ctx)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        require_specific_guild(guild_id, guild.id)

        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete(guild_id, message_id, emoji)

        await message.clear_reaction(emoji)

        await ctx.followup.send(
            content=f"L'emoji {emoji} a bien été retiré du message.\n**Message** : {message_link}"
        )

    @reactionrole.command(name="clear", description="Retire toutes les réactions d'un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def rr_clear(self, ctx: discord.ApplicationContext, message_link: str) -> None:
        """Commande slash /reactionrole clear : retire toutes les réactions d'un message.
        
        Vérifie les permissions du bot,supprime toutes les réactions du message,
        et supprime toutes les règles de rôle par réaction correspondantes de la base de données.
        """
        await ctx.defer(ephemeral=True)
        
        guild, _channel = require_guild_ctx(ctx)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        require_specific_guild(guild_id, guild.id)

        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete_message(guild_id, message_id)

        await message.clear_reactions()

        await ctx.followup.send(
            content=f"Toutes les réactions ont été supprimées du message sélectionné.\n**Message** : {message_link}"
        )


    @reactionrole.command(name="list", description="Affiche la liste des tous les rôles attribués avec une réaction à un message.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def rr_list(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /reactionrole list : affiche la liste des tous les rôles attribués avec une réaction à un message.
        
        Récupère les règles de rôle par réaction du serveur, les organise par message, et affiche le tout dans un embed paginé.
        """
        await ctx.defer(ephemeral=True)

        guild, _channel = require_guild_ctx(ctx)
        guild_id = guild.id
        role_config_guild_list = self.role.rr_list_by_guild_grouped(guild_id)

        paginator = Paginator(
            items=role_config_guild_list,
            embed_generator=build_list_roles_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)


def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog ReactionRoles, appelée lors du chargement de l'extension."""
    bot.add_cog(ReactionRoles(bot))
