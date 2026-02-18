"""Cog de gestion des rôles par réaction, permettant d'associer des réactions à des rôles sur des messages spécifiques.
    
Gère les événements de réaction pour attribuer ou retirer les rôles correspondants, et inclut des commandes pour ajouter,
supprimer et lister les associations de réactions et de rôles.
"""
import logging

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.roles.embeds import build_list_roles_embed
from eldoria.utils.discord_utils import extract_id_from_link, get_text_or_thread_channel

log = logging.getLogger(__name__)

class ReactionRoles(commands.Cog):
    """Cog de gestion des rôles par réaction, permettant d'associer des réactions à des rôles sur des messages spécifiques.
    
    Gère les événements de réaction pour attribuer ou retirer les rôles correspondants, et inclut des commandes pour ajouter,
    supprimer et lister les associations de réactions et de rôles.
    """

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
    @commands.slash_command(name="add_reaction_role", description="Associe une réaction sur un message défini à un rôle.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.option("emoji", str, description="L'émoji de la réaction.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_reaction_role(self, ctx: discord.ApplicationContext, message_link: str, emoji: str, role: discord.Role) -> None:
        """Commande slash /add_reaction_role : associe une réaction sur un message défini à un rôle.
        
        Vérifie les permissions du bot, les conflits d'association existants, ajoute la réaction au message,
        et enregistre la règle de rôle par réaction dans la base de données.
        """
        await ctx.defer(ephemeral=True)

        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        if guild_id is None or channel_id is None or message_id is None:
            await ctx.followup.send(content="Lien de message invalide.")
            return

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        guild = ctx.guild
        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        bot_member = guild.me
        if bot_member is None:
            await ctx.followup.send(content="Je ne suis pas correctement initialisé sur ce serveur.")
            return
        bot_highest_role = max(bot_member.roles, key=lambda r: r.position)

        if role.position >= bot_highest_role.position:
            await ctx.followup.send(
                content=f"Je ne peux pas attribuer le rôle <@&{role.id}> car il est au-dessus de mes permissions."
            )
            return

        existing = self.role.rr_list_by_message(guild_id, message_id)  # dict: {emoji: role_id}

        for existing_emoji, existing_role_id in existing.items():
            if existing_role_id == role.id and existing_emoji != emoji:
                await ctx.followup.send(
                    content=f"Le rôle <@&{role.id}> est déjà associé à l'emoji {existing_emoji} sur le même message."
                )
                return
            if existing_role_id != role.id and existing_emoji == emoji:
                await ctx.followup.send(
                    content=f"L'emoji {existing_emoji} est déjà associé au rôle <@&{existing_role_id}> sur le même message."
                )
                return

        await bot_member.add_roles(role)
        await bot_member.remove_roles(role)
        await message.add_reaction(emoji)

        self.role.rr_upsert(guild_id, message_id, emoji, role.id)

        await ctx.followup.send(
            content=f"## La réaction {emoji} est bien associée au rôle <@&{role.id}> sur le message sélectionné ! \n"
                    f"**Message :** {message_link}\n {message.content}"
        )


    @commands.slash_command(name="remove_specific_reaction", description="Retire une réaction spécifique d'un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.option("emoji", str, description="L'émoji de la réaction.")
    @discord.default_permissions(manage_roles=True, manage_messages=True)
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def remove_specific_reaction(self, ctx: discord.ApplicationContext, message_link: str, emoji: str) -> None:
        """Commande slash /remove_specific_reaction : retire une réaction spécifique d'un message.
        
        Vérifie les permissions du bot, supprime la réaction du message,
        et supprime la règle de rôle par réaction correspondante de la base de données.
        """
        await ctx.defer(ephemeral=True)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        if guild_id is None or channel_id is None or message_id is None:
            await ctx.followup.send(content="Lien de message invalide.")
            return

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete(guild_id, message_id, emoji)


        await message.clear_reaction(emoji)

        await ctx.followup.send(
            content=f"## L'emoji {emoji} a bien été retiré du message.\n**Message** : {message_link}\n{message.content}"
        )

    @commands.slash_command(name="remove_all_reactions", description="Retire toutes les réaction d'un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.default_permissions(manage_roles=True, manage_messages=True)
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def remove_all_reactions(self, ctx: discord.ApplicationContext, message_link: str) -> None:
        """Commande slash /remove_all_reactions : retire toutes les réactions d'un message.
        
        Vérifie les permissions du bot,supprime toutes les réactions du message,
        et supprime toutes les règles de rôle par réaction correspondantes de la base de données.
        """
        await ctx.defer(ephemeral=True)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)
        if guild_id is None or channel_id is None or message_id is None:
            await ctx.followup.send(content="Lien de message invalide.")
            return

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        channel = await get_text_or_thread_channel(self.bot, channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete_message(guild_id, message_id)

        await message.clear_reactions()

        await ctx.followup.send(
            content=f"## Toutes les réactions ont été supprimées du message sélectionné.\n**Message** : {message_link}\n{message.content}"
        )


    @commands.slash_command(name="list_of_reaction_roles",description="Affiche la liste des tous les rôles attribués avec une réaction à un message.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def list_reaction_roles(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /list_reaction_roles : affiche la liste des tous les rôles attribués avec une réaction à un message.
        
        Récupère les règles de rôle par réaction du serveur, les organise par message, et affiche le tout dans un embed paginé.
        """
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        role_config_guild_list = self.role.rr_list_by_guild_grouped(guild_id)

        await ctx.defer(ephemeral=True)
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
