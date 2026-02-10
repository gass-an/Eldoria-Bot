import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.roles.embeds import build_list_roles_embed
from eldoria.utils.discord_utils import extract_id_from_link


class ReactionRoles(commands.Cog):
    def __init__(self, bot: EldoriaBot):
        self.bot = bot
        self.role = self.bot.services.role

    # -------------------- Events --------------------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None or member == self.bot.user:
            return

        role_id = self.role.rr_get_role_id(payload.guild_id, payload.message_id, payload.emoji.name)
        if role_id is None:
            return

        role = guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        role_id = self.role.rr_get_role_id(payload.guild_id, payload.message_id, payload.emoji.name)
        if role_id is None:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member:
            try:
                await member.remove_roles(role)
            except (discord.Forbidden, discord.HTTPException):
                pass

    # -------------------- Commands --------------------
    @commands.slash_command(name="add_reaction_role", description="Associe une réaction sur un message défini à un rôle.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.option("emoji", str, description="L'émoji de la réaction.")
    @discord.option("role", discord.Role, description="Le rôle attribué.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_reaction_role(self, ctx: discord.ApplicationContext, message_link: str, emoji: str, role: discord.Role):
        await ctx.defer(ephemeral=True)

        guild_id, channel_id, message_id = extract_id_from_link(message_link)

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        guild = ctx.guild
        channel = await self.bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        bot_member = guild.get_member(self.bot.user.id)
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

        try:
            await bot_member.add_roles(role)
            await bot_member.remove_roles(role)
            await message.add_reaction(emoji)
        except discord.NotFound:
            await ctx.followup.send(content="Message ou canal introuvable.")
            return
        except discord.Forbidden:
            await ctx.followup.send(content=(
                "## Un problème est survenu : \n"
                "- Soit je n'ai pas le droit de rajouter une réaction sur ce message.\n"
                "- Soit je n'ai pas le droit de gérer ce rôle."
            ))
            return

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
    async def remove_specific_reaction(self, ctx: discord.ApplicationContext, message_link: str, emoji: str):
        await ctx.defer(ephemeral=True)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        channel = await self.bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete(guild_id, message_id, emoji)

        try:
            await message.clear_reaction(emoji)
        except discord.Forbidden:
            await ctx.followup.send(content="Je n'ai pas la permission de supprimer les réactions.")
            return

        await ctx.followup.send(
            content=f"## L'emoji {emoji} a bien été retiré du message.\n**Message** : {message_link}\n{message.content}"
        )

    @commands.slash_command(name="remove_all_reactions", description="Retire toutes les réaction d'un message.")
    @discord.option("message_link", str, description="Le lien du message qui contiendra la réaction.")
    @discord.default_permissions(manage_roles=True, manage_messages=True)
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def remove_all_reactions(self, ctx: discord.ApplicationContext, message_link: str):
        await ctx.defer(ephemeral=True)
        guild_id, channel_id, message_id = extract_id_from_link(message_link)

        if ctx.guild is None or guild_id != ctx.guild.id:
            await ctx.followup.send(content="Le lien que vous m'avez fourni provient d'un autre serveur.")
            return

        channel = await self.bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)

        self.role.rr_delete_message(guild_id, message_id)

        try:
            await message.clear_reactions()
        except discord.Forbidden:
            await ctx.followup.send(content="Je n'ai pas la permission de supprimer les réactions.")
            return

        await ctx.followup.send(
            content=f"## Toutes les réactions ont été supprimées du message sélectionné.\n**Message** : {message_link}\n{message.content}"
        )


    @commands.slash_command(name="list_of_reaction_roles",description="Affiche la liste des tous les rôles attribués avec une réaction à un message.")
    @discord.default_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def list_reaction_roles(self, ctx: discord.ApplicationContext):
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


def setup(bot: EldoriaBot):
    bot.add_cog(ReactionRoles(bot))
