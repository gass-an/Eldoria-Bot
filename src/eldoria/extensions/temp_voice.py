import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.temp_voice.embeds import build_list_temp_voice_parents_embed

from ..db import database_manager
from ..ui.common import pagination


class TempVoice(commands.Cog):
    def __init__(self, bot: EldoriaBot):
        self.bot = bot

    # -------------------- Events --------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild

        # 1) DELETE d'abord : si on quitte un salon temporaire et qu'il devient vide
        if before.channel:
            parent_id = database_manager.tv_find_parent_of_active(guild.id, before.channel.id)
            if parent_id is not None and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                finally:
                    database_manager.tv_remove_active(guild.id, parent_id, before.channel.id)

        # 2) GARDE-FOU : si on arrive déjà dans un salon temporaire, on ne crée rien
        if after.channel:
            if database_manager.tv_find_parent_of_active(guild.id, after.channel.id) is not None:
                return

            # 3) CREATE : uniquement si after.channel est un "parent" configuré
            user_limit = database_manager.tv_get_parent(guild.id, after.channel.id)
            if user_limit is not None:
                category = after.channel.category
                new_channel_name = f"Salon de {member.display_name}"
                overwrites = {
                    member: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
                }

                new_channel = await guild.create_voice_channel(
                    name=new_channel_name,
                    category=category,
                    overwrites=overwrites,
                    bitrate=after.channel.bitrate,
                    user_limit=user_limit,
                )

                # Important : enregistrer AVANT le move pour que le 2e event (move) soit filtré
                database_manager.tv_add_active(guild.id, after.channel.id, new_channel.id)

                await member.move_to(new_channel)

    # -------------------- Commands --------------------
    @commands.slash_command(
        name="init_creation_voice_channel",
        description="Défini le salon qui permettra à chacun de créer son propre salon vocal temporaire",
    )
    @discord.option("channel", discord.VoiceChannel, description="Le channel cible pour la création d'autres salon vocaux.")
    @discord.option("user_limit", int, description="Le nombre de personnes qui pourront rejoindre les salons créés", min_value=1, max_value=99)
    @discord.default_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def init_creation_voice_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel, user_limit: int):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        channel_id = channel.id
        database_manager.tv_upsert_parent(guild_id, channel_id, user_limit)

        await ctx.followup.send(content=f"Le salon {channel.mention} est désormais paramétré pour créer des salons pour {user_limit} personnes maximum")

    @commands.slash_command(
        name="remove_creation_voice_channel",
        description="Désactive la création automatique de salons vocaux temporaires pour un salon donné",
    )
    @discord.option("channel", discord.VoiceChannel, description="Le salon parent à désactiver")
    @discord.default_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def remove_creation_voice_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild_id = ctx.guild.id
        channel_id = channel.id

        if database_manager.tv_get_parent(guild_id, channel_id) is None:
            await ctx.followup.send(content=f"❌ Le salon {channel.mention} n'est pas configuré comme salon parent.")
            return

        database_manager.tv_delete_parent(guild_id, channel_id)

        await ctx.followup.send(content=f"✅ Le salon {channel.mention} n'est plus un salon de création automatique.")

    @commands.slash_command(
        name="list_creation_voice_channels",
        description="Affiche la liste des salons parents qui créent des vocaux temporaires.",
    )
    @discord.default_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def list_creation_voice_channels(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        parents = database_manager.tv_list_parents(guild_id)

        await ctx.defer(ephemeral=True)
        paginator = pagination.Paginator(
            items=parents,
            embed_generator=build_list_temp_voice_parents_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)


def setup(bot: EldoriaBot):
    bot.add_cog(TempVoice(bot))
